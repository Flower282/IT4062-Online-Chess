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
#include <netdb.h>
#include <poll.h>
#include <fcntl.h>

/* ========== Global State ========== */

static int client_fd = -1;                          /* Client socket descriptor */
static uint8_t recv_buffer[BUFFER_SIZE];            /* Receive buffer */
static size_t recv_offset = 0;                      /* Current offset in recv buffer */
static uint8_t send_buffer[BUFFER_SIZE];            /* Send buffer */
static int connected_flag = 0;                      /* Connection status */
static NetworkEvent event_queue[1024];              /* Event queue */
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

/* Process received data and extract complete messages */
static void process_received_data(void) {
    while (recv_offset >= HEADER_SIZE) {
        /* Parse header */
        MessageHeader* header = (MessageHeader*)recv_buffer;
        uint16_t message_id = ntohs(header->message_id);
        uint32_t payload_length = ntohl(header->payload_length);
        
        /* Check if we have complete message */
        if (recv_offset < HEADER_SIZE + payload_length) {
            break; /* Need more data */
        }
        
        /* Extract payload */
        uint8_t* payload_data = NULL;
        if (payload_length > 0) {
            payload_data = malloc(payload_length);
            if (payload_data) {
                memcpy(payload_data, recv_buffer + HEADER_SIZE, payload_length);
            }
        }
        
        /* Enqueue message event */
        NetworkEvent event = {
            .type = EVENT_MESSAGE_RECEIVED,
            .message_id = message_id,
            .payload_length = payload_length,
            .payload_data = payload_data
        };
        enqueue_event(event);
        
        /* Remove processed message from buffer */
        size_t message_size = HEADER_SIZE + payload_length;
        memmove(recv_buffer, 
                recv_buffer + message_size,
                recv_offset - message_size);
        recv_offset -= message_size;
    }
}

/* ========== Client API Implementation ========== */

int client_init(const char* host, int port) {
    struct sockaddr_in server_addr;
    struct hostent* server;
    
    /* Create socket */
    client_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (client_fd == -1) {
        perror("socket");
        return -1;
    }
    
    /* Resolve hostname */
    server = gethostbyname(host);
    if (server == NULL) {
        fprintf(stderr, "ERROR: Host not found: %s\n", host);
        close(client_fd);
        client_fd = -1;
        return -1;
    }
    
    /* Setup server address */
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    memcpy(&server_addr.sin_addr.s_addr, server->h_addr, server->h_length);
    server_addr.sin_port = htons(port);
    
    /* Connect to server */
    if (connect(client_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) == -1) {
        perror("connect");
        close(client_fd);
        client_fd = -1;
        return -1;
    }
    
    /* Set non-blocking mode */
    if (set_nonblocking(client_fd) == -1) {
        close(client_fd);
        client_fd = -1;
        return -1;
    }
    
    /* Initialize state */
    recv_offset = 0;
    connected_flag = 1;
    
    /* Enqueue connected event */
    NetworkEvent event = {
        .type = EVENT_CONNECTED,
        .message_id = 0,
        .payload_length = 0,
        .payload_data = NULL
    };
    enqueue_event(event);
    
    printf("Connected to %s:%d\n", host, port);
    return 0;
}

void client_shutdown(void) {
    if (client_fd != -1) {
        close(client_fd);
        client_fd = -1;
    }
    
    connected_flag = 0;
    recv_offset = 0;
    
    /* Enqueue disconnected event */
    NetworkEvent event = {
        .type = EVENT_DISCONNECTED,
        .message_id = 0,
        .payload_length = 0,
        .payload_data = NULL
    };
    enqueue_event(event);
    
    printf("Disconnected from server\n");
}

int client_poll(int timeout_ms) {
    if (!connected_flag || client_fd == -1) {
        return -1;
    }
    
    struct pollfd pfd;
    pfd.fd = client_fd;
    pfd.events = POLLIN;
    pfd.revents = 0;
    
    int poll_count = poll(&pfd, 1, timeout_ms);
    
    if (poll_count == -1) {
        perror("poll");
        return -1;
    }
    
    if (poll_count == 0) {
        return 0; /* Timeout */
    }
    
    /* Check for errors */
    if (pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) {
        fprintf(stderr, "Connection error\n");
        client_shutdown();
        return -1;
    }
    
    /* Handle incoming data */
    if (pfd.revents & POLLIN) {
        ssize_t bytes_received = recv(client_fd, 
                                       recv_buffer + recv_offset,
                                       BUFFER_SIZE - recv_offset,
                                       0);
        
        if (bytes_received <= 0) {
            if (bytes_received == 0 || (errno != EWOULDBLOCK && errno != EAGAIN)) {
                /* Connection closed or error */
                client_shutdown();
                return -1;
            }
        } else {
            recv_offset += bytes_received;
            process_received_data();
        }
    }
    
    return poll_count;
}

int client_send_message(uint16_t message_id, const uint8_t* payload, uint32_t payload_length) {
    if (!connected_flag || client_fd == -1) {
        fprintf(stderr, "Not connected to server\n");
        return -1;
    }
    
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
    memcpy(send_buffer, &header, HEADER_SIZE);
    if (payload_length > 0 && payload) {
        memcpy(send_buffer + HEADER_SIZE, payload, payload_length);
    }
    
    /* Send data */
    ssize_t bytes_sent = send(client_fd, send_buffer, total_size, 0);
    if (bytes_sent == -1) {
        if (errno != EWOULDBLOCK && errno != EAGAIN) {
            perror("send");
            client_shutdown();
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

int is_connected(void) {
    return connected_flag;
}

const char* get_message_type_name(uint16_t message_id) {
    switch (message_id) {
        /* C2S */
        case MSG_C2S_REGISTER: return "REGISTER";
        case MSG_C2S_LOGIN: return "LOGIN";
        case MSG_C2S_GET_ONLINE_USERS: return "GET_ONLINE_USERS";
        case MSG_C2S_FIND_MATCH: return "FIND_MATCH";
        case MSG_C2S_CANCEL_FIND_MATCH: return "CANCEL_FIND_MATCH";
        case MSG_C2S_FIND_AI_MATCH: return "FIND_AI_MATCH";
        case MSG_C2S_MAKE_MOVE: return "MAKE_MOVE";
        case MSG_C2S_RESIGN: return "RESIGN";
        case MSG_C2S_OFFER_DRAW: return "OFFER_DRAW";
        case MSG_C2S_ACCEPT_DRAW: return "ACCEPT_DRAW";
        case MSG_C2S_DECLINE_DRAW: return "DECLINE_DRAW";
        case MSG_C2S_CHALLENGE: return "CHALLENGE";
        case MSG_C2S_ACCEPT_CHALLENGE: return "ACCEPT_CHALLENGE";
        case MSG_C2S_DECLINE_CHALLENGE: return "DECLINE_CHALLENGE";
        case MSG_C2S_GET_STATS: return "GET_STATS";
        case MSG_C2S_GET_HISTORY: return "GET_HISTORY";
        
        /* S2C */
        case MSG_S2C_REGISTER_RESULT: return "REGISTER_RESULT";
        case MSG_S2C_LOGIN_RESULT: return "LOGIN_RESULT";
        case MSG_S2C_USER_STATUS_UPDATE: return "USER_STATUS_UPDATE";
        case MSG_S2C_ONLINE_USERS_LIST: return "ONLINE_USERS_LIST";
        case MSG_S2C_MATCH_FOUND: return "MATCH_FOUND";
        case MSG_S2C_GAME_START: return "GAME_START";
        case MSG_S2C_GAME_STATE_UPDATE: return "GAME_STATE_UPDATE";
        case MSG_S2C_INVALID_MOVE: return "INVALID_MOVE";
        case MSG_S2C_GAME_OVER: return "GAME_OVER";
        case MSG_S2C_DRAW_OFFER_RECEIVED: return "DRAW_OFFER_RECEIVED";
        case MSG_S2C_DRAW_OFFER_DECLINED: return "DRAW_OFFER_DECLINED";
        case MSG_S2C_CHALLENGE_RECEIVED: return "CHALLENGE_RECEIVED";
        case MSG_S2C_CHALLENGE_ACCEPTED: return "CHALLENGE_ACCEPTED";
        case MSG_S2C_CHALLENGE_DECLINED: return "CHALLENGE_DECLINED";
        case MSG_S2C_STATS_RESPONSE: return "STATS_RESPONSE";
        case MSG_S2C_HISTORY_RESPONSE: return "HISTORY_RESPONSE";
        
        default: return "UNKNOWN";
    }
}
