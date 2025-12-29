#include "protocol.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <poll.h>
#include <fcntl.h>

/* ========== Global State ========== */

static int listener_fd = -1;                     /* Listening socket */
static struct pollfd ufds[MAX_CLIENTS + 1];      /* Poll file descriptors (+1 for listener) */
static ClientSession clients[MAX_CLIENTS];       /* Client session array */
static int fd_count = 0;                         /* Number of active file descriptors */
static NetworkEvent event_queue[1024];           /* Event queue for Python */
static int event_queue_head = 0;
static int event_queue_tail = 0;
static int event_queue_count = 0;

/* ========== Helper Functions ========== */

/* Set socket to non-blocking mode */
static int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags == -1) {
        perror("fcntl F_GETFL");
        return -1;
    }
    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1) {
        perror("fcntl F_SETFL");
        return -1;
    }
    return 0;
}

/* Add event to queue */
static void enqueue_event(NetworkEvent event) {
    if (event_queue_count >= 1024) {
        fprintf(stderr, "Event queue full, dropping event\n");
        if (event.payload_data) {
            free(event.payload_data);
        }
        return;
    }
    event_queue[event_queue_tail] = event;
    event_queue_tail = (event_queue_tail + 1) % 1024;
    event_queue_count++;
}

/* Find client index by file descriptor */
static int find_client_index(int fd) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].fd == fd) {
            return i;
        }
    }
    return -1;
}

/* Find pollfd index by file descriptor */
static int find_pollfd_index(int fd) {
    for (int i = 0; i < fd_count; i++) {
        if (ufds[i].fd == fd) {
            return i;
        }
    }
    return -1;
}

/* Add new file descriptor to poll array */
static int add_to_poll(int fd) {
    if (fd_count >= MAX_CLIENTS + 1) {
        fprintf(stderr, "Maximum clients reached\n");
        return -1;
    }
    ufds[fd_count].fd = fd;
    ufds[fd_count].events = POLLIN;
    fd_count++;
    return 0;
}

/* Remove file descriptor from poll array */
static void remove_from_poll(int fd) {
    int index = find_pollfd_index(fd);
    if (index == -1) {
        return;
    }
    
    /* Move last element to this position */
    if (index < fd_count - 1) {
        ufds[index] = ufds[fd_count - 1];
    }
    fd_count--;
}

/* Initialize client session */
static void init_client_session(int index, int fd) {
    clients[index].fd = fd;
    clients[index].state = CLIENT_CONNECTED;
    clients[index].recv_offset = 0;
    clients[index].send_offset = 0;
    clients[index].send_length = 0;
    clients[index].username[0] = '\0';
    clients[index].user_id = 0;
    clients[index].game_id = -1;
    memset(clients[index].recv_buffer, 0, BUFFER_SIZE);
    memset(clients[index].send_buffer, 0, BUFFER_SIZE);
}

/* ========== Server Management Functions ========== */

int server_init(int port) {
    struct sockaddr_in server_addr;
    
    /* Initialize client array */
    for (int i = 0; i < MAX_CLIENTS; i++) {
        clients[i].fd = -1;
        clients[i].state = CLIENT_DISCONNECTED;
    }
    
    /* Create listening socket */
    listener_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listener_fd == -1) {
        perror("socket");
        return -1;
    }
    
    /* Set socket options */
    int opt = 1;
    if (setsockopt(listener_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1) {
        perror("setsockopt");
        close(listener_fd);
        return -1;
    }
    
    /* Set non-blocking */
    if (set_nonblocking(listener_fd) == -1) {
        close(listener_fd);
        return -1;
    }
    
    /* Bind to port */
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);
    
    if (bind(listener_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) == -1) {
        perror("bind");
        close(listener_fd);
        return -1;
    }
    
    /* Listen for connections */
    if (listen(listener_fd, 10) == -1) {
        perror("listen");
        close(listener_fd);
        return -1;
    }
    
    /* Add listener to poll array */
    ufds[0].fd = listener_fd;
    ufds[0].events = POLLIN;
    fd_count = 1;
    
    printf("TCP Server initialized on port %d\n", port);
    return 0;
}

void server_shutdown(void) {
    /* Close all client connections */
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].fd != -1) {
            close(clients[i].fd);
            clients[i].fd = -1;
        }
    }
    
    /* Close listener socket */
    if (listener_fd != -1) {
        close(listener_fd);
        listener_fd = -1;
    }
    
    fd_count = 0;
    printf("Server shutdown complete\n");
}

/* Handle new incoming connection */
static void handle_new_connection(void) {
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    
    int new_fd = accept(listener_fd, (struct sockaddr*)&client_addr, &addr_len);
    if (new_fd == -1) {
        if (errno != EWOULDBLOCK && errno != EAGAIN) {
            perror("accept");
        }
        return;
    }
    
    /* Set non-blocking */
    if (set_nonblocking(new_fd) == -1) {
        close(new_fd);
        return;
    }
    
    /* Find free slot in client array */
    int client_index = -1;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].fd == -1) {
            client_index = i;
            break;
        }
    }
    
    if (client_index == -1) {
        fprintf(stderr, "No free client slots\n");
        close(new_fd);
        return;
    }
    
    /* Add to poll array */
    if (add_to_poll(new_fd) == -1) {
        close(new_fd);
        return;
    }
    
    /* Initialize client session */
    init_client_session(client_index, new_fd);
    
    /* Enqueue new connection event */
    NetworkEvent event = {
        .type = EVENT_NEW_CONNECTION,
        .client_fd = new_fd,
        .message_id = 0,
        .payload_length = 0,
        .payload_data = NULL
    };
    enqueue_event(event);
    
    printf("New connection from %s:%d (fd=%d)\n",
           inet_ntoa(client_addr.sin_addr),
           ntohs(client_addr.sin_port),
           new_fd);
}

/* Process received data and extract complete messages */
static void process_client_data(int client_index) {
    ClientSession* client = &clients[client_index];
    
    while (client->recv_offset >= HEADER_SIZE) {
        /* Parse header */
        MessageHeader* header = (MessageHeader*)client->recv_buffer;
        uint16_t message_id = ntohs(header->message_id);
        uint32_t payload_length = ntohl(header->payload_length);
        
        /* Check if we have complete message */
        if (client->recv_offset < HEADER_SIZE + payload_length) {
            break; /* Need more data */
        }
        
        /* Extract payload */
        uint8_t* payload_data = NULL;
        if (payload_length > 0) {
            payload_data = malloc(payload_length);
            if (payload_data) {
                memcpy(payload_data, client->recv_buffer + HEADER_SIZE, payload_length);
            }
        }
        
        /* Enqueue message event */
        NetworkEvent event = {
            .type = EVENT_MESSAGE_RECEIVED,
            .client_fd = client->fd,
            .message_id = message_id,
            .payload_length = payload_length,
            .payload_data = payload_data
        };
        enqueue_event(event);
        
        /* Remove processed message from buffer */
        size_t message_size = HEADER_SIZE + payload_length;
        memmove(client->recv_buffer, 
                client->recv_buffer + message_size,
                client->recv_offset - message_size);
        client->recv_offset -= message_size;
    }
}

/* Handle data from client */
static void handle_client_data(int fd) {
    int client_index = find_client_index(fd);
    if (client_index == -1) {
        return;
    }
    
    ClientSession* client = &clients[client_index];
    
    /* Receive data */
    ssize_t bytes_received = recv(fd, 
                                   client->recv_buffer + client->recv_offset,
                                   BUFFER_SIZE - client->recv_offset,
                                   0);
    
    if (bytes_received <= 0) {
        if (bytes_received == 0 || (errno != EWOULDBLOCK && errno != EAGAIN)) {
            /* Connection closed or error */
            disconnect_client(fd);
        }
        return;
    }
    
    client->recv_offset += bytes_received;
    
    /* Process received data */
    process_client_data(client_index);
}

/* Main poll loop */
int server_poll(int timeout_ms) {
    int poll_count = poll(ufds, fd_count, timeout_ms);
    
    if (poll_count == -1) {
        perror("poll");
        return -1;
    }
    
    if (poll_count == 0) {
        return 0; /* Timeout */
    }
    
    /* Check for events */
    for (int i = 0; i < fd_count; i++) {
        if (ufds[i].revents == 0) {
            continue;
        }
        
        /* Check for errors */
        if (ufds[i].revents & (POLLERR | POLLHUP | POLLNVAL)) {
            if (ufds[i].fd != listener_fd) {
                disconnect_client(ufds[i].fd);
            }
            continue;
        }
        
        /* Handle events */
        if (ufds[i].revents & POLLIN) {
            if (ufds[i].fd == listener_fd) {
                /* New connection */
                handle_new_connection();
            } else {
                /* Data from client */
                handle_client_data(ufds[i].fd);
            }
        }
    }
    
    return poll_count;
}

/* ========== Message Handling Functions ========== */

int send_message(int client_fd, uint16_t message_id, const uint8_t* payload, uint32_t payload_length) {
    int client_index = find_client_index(client_fd);
    if (client_index == -1) {
        fprintf(stderr, "Client fd %d not found\n", client_fd);
        return -1;
    }
    
    ClientSession* client = &clients[client_index];
    
    /* Prepare header */
    MessageHeader header;
    header.message_id = htons(message_id);
    header.payload_length = htonl(payload_length);
    
    /* Calculate total size */
    size_t total_size = HEADER_SIZE + payload_length;
    if (total_size > BUFFER_SIZE) {
        fprintf(stderr, "Message too large: %zu bytes\n", total_size);
        return -1;
    }
    
    /* Build message in send buffer */
    memcpy(client->send_buffer, &header, HEADER_SIZE);
    if (payload_length > 0 && payload) {
        memcpy(client->send_buffer + HEADER_SIZE, payload, payload_length);
    }
    
    /* Send data */
    ssize_t bytes_sent = send(client_fd, client->send_buffer, total_size, 0);
    if (bytes_sent == -1) {
        if (errno != EWOULDBLOCK && errno != EAGAIN) {
            perror("send");
            return -1;
        }
        return 0; /* Would block, try again later */
    }
    
    return bytes_sent;
}

NetworkEvent* get_next_event(void) {
    if (event_queue_count == 0) {
        return NULL;
    }
    
    NetworkEvent* event = malloc(sizeof(NetworkEvent));
    if (!event) {
        return NULL;
    }
    
    *event = event_queue[event_queue_head];
    event_queue_head = (event_queue_head + 1) % 1024;
    event_queue_count--;
    
    return event;
}

void free_event(NetworkEvent* event) {
    if (event) {
        if (event->payload_data) {
            free(event->payload_data);
        }
        free(event);
    }
}

/* ========== Client Management Functions ========== */

ClientSession* get_client_session(int client_fd) {
    int client_index = find_client_index(client_fd);
    if (client_index == -1) {
        return NULL;
    }
    return &clients[client_index];
}

void disconnect_client(int client_fd) {
    int client_index = find_client_index(client_fd);
    if (client_index == -1) {
        return;
    }
    
    /* Enqueue disconnect event */
    NetworkEvent event = {
        .type = EVENT_CLIENT_DISCONNECTED,
        .client_fd = client_fd,
        .message_id = 0,
        .payload_length = 0,
        .payload_data = NULL
    };
    enqueue_event(event);
    
    /* Remove from poll array */
    remove_from_poll(client_fd);
    
    /* Close socket */
    close(client_fd);
    
    /* Reset client session */
    clients[client_index].fd = -1;
    clients[client_index].state = CLIENT_DISCONNECTED;
    
    printf("Client disconnected (fd=%d)\n", client_fd);
}

int get_client_count(void) {
    int count = 0;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].fd != -1) {
            count++;
        }
    }
    return count;
}

/* ========== Utility Functions ========== */

const char* get_message_type_name(uint16_t message_id) {
    switch (message_id) {
        /* C2S */
        case MSG_C2S_REGISTER: return "REGISTER";
        case MSG_C2S_LOGIN: return "LOGIN";
        case MSG_C2S_FIND_MATCH: return "FIND_MATCH";
        case MSG_C2S_CANCEL_FIND_MATCH: return "CANCEL_FIND_MATCH";
        case MSG_C2S_FIND_AI_MATCH: return "FIND_AI_MATCH";
        case MSG_C2S_MAKE_MOVE: return "MAKE_MOVE";
        case MSG_C2S_RESIGN: return "RESIGN";
        case MSG_C2S_OFFER_DRAW: return "OFFER_DRAW";
        case MSG_C2S_ACCEPT_DRAW: return "ACCEPT_DRAW";
        case MSG_C2S_DECLINE_DRAW: return "DECLINE_DRAW";
        case MSG_C2S_GET_STATS: return "GET_STATS";
        case MSG_C2S_GET_HISTORY: return "GET_HISTORY";
        case MSG_C2S_GET_REPLAY: return "GET_REPLAY";
        
        /* S2C */
        case MSG_S2C_REGISTER_RESULT: return "REGISTER_RESULT";
        case MSG_S2C_LOGIN_RESULT: return "LOGIN_RESULT";
        case MSG_S2C_USER_STATUS_UPDATE: return "USER_STATUS_UPDATE";
        case MSG_S2C_MATCH_FOUND: return "MATCH_FOUND";
        case MSG_S2C_GAME_START: return "GAME_START";
        case MSG_S2C_GAME_STATE_UPDATE: return "GAME_STATE_UPDATE";
        case MSG_S2C_INVALID_MOVE: return "INVALID_MOVE";
        case MSG_S2C_GAME_OVER: return "GAME_OVER";
        case MSG_S2C_DRAW_OFFER_RECEIVED: return "DRAW_OFFER_RECEIVED";
        case MSG_S2C_DRAW_OFFER_DECLINED: return "DRAW_OFFER_DECLINED";
        case MSG_S2C_STATS_RESPONSE: return "STATS_RESPONSE";
        case MSG_S2C_HISTORY_RESPONSE: return "HISTORY_RESPONSE";
        case MSG_S2C_REPLAY_DATA: return "REPLAY_DATA";
        
        default: return "UNKNOWN";
    }
}
