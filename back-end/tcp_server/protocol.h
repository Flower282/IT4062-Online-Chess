#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>
#include <stddef.h>

/* ========== Message Type Definitions ========== */

/* Client to Server (C2S) Message Types */
typedef enum {
    /* Authentication */
    MSG_C2S_REGISTER            = 0x0001,
    MSG_C2S_LOGIN               = 0x0002,
    MSG_C2S_GET_ONLINE_USERS    = 0x0003,
    
    /* Matchmaking */
    MSG_C2S_FIND_MATCH          = 0x0010,
    MSG_C2S_CANCEL_FIND_MATCH   = 0x0011,
    MSG_C2S_FIND_AI_MATCH       = 0x0012,
    
    /* Game Actions */
    MSG_C2S_MAKE_MOVE           = 0x0020,
    MSG_C2S_RESIGN              = 0x0021,
    MSG_C2S_OFFER_DRAW          = 0x0022,
    MSG_C2S_ACCEPT_DRAW         = 0x0023,
    MSG_C2S_DECLINE_DRAW        = 0x0024,
    
    /* Statistics & History */
    MSG_C2S_GET_STATS           = 0x0030,
    MSG_C2S_GET_HISTORY         = 0x0031,
    MSG_C2S_GET_REPLAY          = 0x0032
} MessageTypeC2S;

/* Server to Client (S2C) Message Types */
typedef enum {
    /* Authentication Responses */
    MSG_S2C_REGISTER_RESULT     = 0x1001,
    MSG_S2C_LOGIN_RESULT        = 0x1002,
    MSG_S2C_USER_STATUS_UPDATE  = 0x1003,
    MSG_S2C_ONLINE_USERS_LIST   = 0x1004,
    
    /* Matchmaking Responses */
    MSG_S2C_MATCH_FOUND         = 0x1100,
    MSG_S2C_GAME_START          = 0x1101,
    
    /* Game State Updates */
    MSG_S2C_GAME_STATE_UPDATE   = 0x1200,
    MSG_S2C_INVALID_MOVE        = 0x1201,
    MSG_S2C_GAME_OVER           = 0x1202,
    MSG_S2C_DRAW_OFFER_RECEIVED = 0x1203,
    MSG_S2C_DRAW_OFFER_DECLINED = 0x1204,
    
    /* Statistics & History Responses */
    MSG_S2C_STATS_RESPONSE      = 0x1300,
    MSG_S2C_HISTORY_RESPONSE    = 0x1301,
    MSG_S2C_REPLAY_DATA         = 0x1302
} MessageTypeS2C;

/* ========== Protocol Header Structure ========== */

/* Fixed header for all TCP messages (6 bytes total) */
typedef struct {
    uint16_t message_id;      /* Message type identifier (2 bytes) */
    uint32_t payload_length;  /* Length of payload in bytes (4 bytes) */
} __attribute__((packed)) MessageHeader;

/* Complete message structure */
typedef struct {
    MessageHeader header;
    uint8_t* payload;         /* Dynamic payload data */
} Message;

/* ========== Connection Management ========== */

#define MAX_CLIENTS 1024
#define BUFFER_SIZE 65536
#define HEADER_SIZE sizeof(MessageHeader)

/* Client connection state */
typedef enum {
    CLIENT_DISCONNECTED = 0,
    CLIENT_CONNECTED,
    CLIENT_AUTHENTICATED,
    CLIENT_IN_GAME
} ClientState;

/* Client session information */
typedef struct {
    int fd;                          /* Socket file descriptor */
    ClientState state;               /* Connection state */
    uint8_t recv_buffer[BUFFER_SIZE]; /* Receive buffer */
    size_t recv_offset;              /* Current offset in receive buffer */
    uint8_t send_buffer[BUFFER_SIZE]; /* Send buffer */
    size_t send_offset;              /* Current offset in send buffer */
    size_t send_length;              /* Total bytes to send */
    char username[64];               /* Authenticated username */
    uint32_t user_id;                /* User ID from database */
    int game_id;                     /* Current game ID (-1 if not in game) */
} ClientSession;

/* ========== Event Structure for Python Bridge ========== */

typedef enum {
    EVENT_NEW_CONNECTION = 1,
    EVENT_CLIENT_DISCONNECTED,
    EVENT_MESSAGE_RECEIVED,
    EVENT_ERROR
} EventType;

/* Event structure passed to Python */
typedef struct {
    EventType type;
    int client_fd;
    uint16_t message_id;
    uint32_t payload_length;
    uint8_t* payload_data;
} NetworkEvent;

/* ========== Function Declarations ========== */

/* Server initialization and main loop */
int server_init(int port);
void server_shutdown(void);
int server_poll(int timeout_ms);

/* Message handling */
int send_message(int client_fd, uint16_t message_id, const uint8_t* payload, uint32_t payload_length);
NetworkEvent* get_next_event(void);
void free_event(NetworkEvent* event);

/* Client management */
ClientSession* get_client_session(int client_fd);
void disconnect_client(int client_fd);
int get_client_count(void);

/* Utility functions */
const char* get_message_type_name(uint16_t message_id);

#endif /* PROTOCOL_H */
