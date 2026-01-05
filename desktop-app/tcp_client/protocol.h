#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/* ========== Constants ========== */

#define BUFFER_SIZE 65536
#define HEADER_SIZE 6

/* ========== Message Type Definitions ========== */

/* Client to Server Messages */
#define MSG_C2S_REGISTER            0x0001
#define MSG_C2S_LOGIN               0x0002
#define MSG_C2S_GET_ONLINE_USERS    0x0003
#define MSG_C2S_FIND_MATCH          0x0010
#define MSG_C2S_CANCEL_FIND_MATCH   0x0011
#define MSG_C2S_FIND_AI_MATCH       0x0012
#define MSG_C2S_MAKE_MOVE           0x0020
#define MSG_C2S_RESIGN              0x0021
#define MSG_C2S_OFFER_DRAW          0x0022
#define MSG_C2S_ACCEPT_DRAW         0x0023
#define MSG_C2S_DECLINE_DRAW        0x0024
#define MSG_C2S_CHALLENGE           0x0025
#define MSG_C2S_ACCEPT_CHALLENGE    0x0026
#define MSG_C2S_DECLINE_CHALLENGE   0x0027
#define MSG_C2S_GET_STATS           0x0030
#define MSG_C2S_GET_HISTORY         0x0031

/* Server to Client Messages */
#define MSG_S2C_REGISTER_RESULT     0x1001
#define MSG_S2C_LOGIN_RESULT        0x1002
#define MSG_S2C_USER_STATUS_UPDATE  0x1003
#define MSG_S2C_ONLINE_USERS_LIST   0x1004
#define MSG_S2C_MATCH_FOUND         0x1100
#define MSG_S2C_GAME_START          0x1101
#define MSG_S2C_GAME_STATE_UPDATE   0x1200
#define MSG_S2C_INVALID_MOVE        0x1201
#define MSG_S2C_GAME_OVER           0x1202
#define MSG_S2C_DRAW_OFFER_RECEIVED 0x1203
#define MSG_S2C_DRAW_OFFER_DECLINED 0x1204
#define MSG_S2C_CHALLENGE_RECEIVED  0x1205
#define MSG_S2C_CHALLENGE_ACCEPTED  0x1206
#define MSG_S2C_CHALLENGE_DECLINED  0x1207
#define MSG_S2C_STATS_RESPONSE      0x1300
#define MSG_S2C_HISTORY_RESPONSE    0x1301

/* ========== Event Types ========== */

#define EVENT_CONNECTED             1
#define EVENT_DISCONNECTED          2
#define EVENT_MESSAGE_RECEIVED      3
#define EVENT_ERROR                 4

/* ========== Structure Definitions ========== */

/* Message header structure (6 bytes) */
typedef struct {
    uint16_t message_id;
    uint32_t payload_length;
} __attribute__((packed)) MessageHeader;

/* Network event structure */
typedef struct {
    int type;
    uint16_t message_id;
    uint32_t payload_length;
    uint8_t* payload_data;
} NetworkEvent;

/* ========== Client API Functions ========== */

/* Initialize and connect to server */
int client_init(const char* host, int port);

/* Disconnect and cleanup */
void client_shutdown(void);

/* Check for events (non-blocking) */
int client_poll(int timeout_ms);

/* Send message to server */
int client_send_message(uint16_t message_id, const uint8_t* payload, uint32_t payload_length);

/* Get next event from queue */
NetworkEvent* get_next_event(void);

/* Free event memory */
void free_event(NetworkEvent* event);

/* Get connection status */
int is_connected(void);

/* Get message type name for debugging */
const char* get_message_type_name(uint16_t message_id);

#endif /* PROTOCOL_H */
