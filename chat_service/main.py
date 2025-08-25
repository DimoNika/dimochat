from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.requests import Request

import uvicorn
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session, aliased
# from sqlalchemy.orm.
from shared.models import User, ChatParticipant, Message, Chat
from shared.token_managment import auth, decode
# from ..shared.models import

app = FastAPI(root_path="/api/chat-service")
# app = FastAPI(root_path="")

# environment variables block
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent / "shared" / ".env"
load_dotenv(env_path)


postgre_user = os.getenv("POSTGRES_USER")
postgre_password = os.getenv("POSTGRES_PASSWORD")
postgres_db = os.getenv("POSTGRES_DB")
# environment variables block


engine = create_engine(f"postgresql+psycopg2://{postgre_user}:{postgre_password}@postgres/{postgres_db}", echo=True)
sessionLocal: Session = sessionmaker(engine)




def extract_access_token_from_header(access_token_header: str):
    try:
        if access_token_header:
            access_token_header_parts = access_token_header.split(" ")  # ["Bearer", "token.abc"]
            return access_token_header_parts[1]
    except Exception as e:
        raise Exception(f"ErorUnknown error occured extracting access token: {str(e)}")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def add(self, user_id, websocket: WebSocket):
        self.active_connections.update({user_id: websocket})

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except AttributeError as e:
            # If AttributeError means other user in chat not connected, its ok. Nothing happends
            pass
        except Exception as e:
            print(f"Un expected ERROR in ConnectionManager.send_personal_message(): {str(e)}")
            

    # async def broadcast(self, message: str):
    #     for connection in self.active_connections:
    #         await connection.send_text(message)

manager = ConnectionManager()


def get_chat(session: Session, user1_id: int, user2_id: int) -> Chat:
    CP1 = aliased(ChatParticipant)
    CP2 = aliased(ChatParticipant)

    chat = (
        session.query(Chat)
        .join(CP1, CP1.chat_id == Chat.id)
        .join(CP2, CP2.chat_id == Chat.id)
        .filter(
            CP1.user_id == user1_id,
            CP2.user_id == user2_id,
            Chat.is_group == False
        )
        .first()
    )
    return chat

def check_for_chat(session: Session, user1_id: int, user2_id: int) -> bool:
    CP1 = aliased(ChatParticipant)
    CP2 = aliased(ChatParticipant)

    chat_exists = (
        session.query(Chat.id)
        .join(CP1, CP1.chat_id == Chat.id)
        .join(CP2, CP2.chat_id == Chat.id)
        .filter(
            CP1.user_id == user1_id,
            CP2.user_id == user2_id,
            Chat.is_group == False
        )
        .first()
    )

    return chat_exists is not None

def get_user_chats(session: Session, user_id: int) -> list[Chat]:
    chats = (
        session.query(Chat)
        .join(ChatParticipant)
        .filter(ChatParticipant.user_id == user_id)
        .all()
    )
    return chats

def get_chat_partner(chat: Chat, user_id: int) -> User | None:
    for participant in chat.participants:
        participant: ChatParticipant
        if participant.user_id != user_id:
            user: User = participant.user
            return {
                "username": user.username,
                "user_id": user.id,
            }
        
    return None  # если вдруг нет второго участника


def get_last_messages_by_chat(session: Session, chat_ids: list[int]) -> dict[int, Message]:
    if not chat_ids:
        return {}

    # Подзапрос для выбора времени последнего сообщения
    subq = (
        session.query(
            Message.chat_id,
            func.max(Message.created_at).label("max_created_at")
        )
        .filter(Message.chat_id.in_(chat_ids))
        .group_by(Message.chat_id)
        .subquery()
    )

    # Подключаем к оригинальным сообщениям
    msg_alias = aliased(Message)

    rows = (
        session.query(msg_alias)
        .join(subq, (msg_alias.chat_id == subq.c.chat_id) & (msg_alias.created_at == subq.c.max_created_at))
        .all()
    )

    # Преобразуем в словарь
    return {msg.chat_id: msg for msg in rows}

def super_func(session: Session, user_id: int):
    data = []

    all_chats = (  # allchats list
        session.query(Chat)
        .join(ChatParticipant)
        .filter(ChatParticipant.user_id == user_id)
        .all()
    )
    
    print("allchats", all_chats)
    for chat in all_chats:

        chat_obj = {}

        chat_obj["chatter"] = get_chat_partner(chat, user_id)        
        
        message = (
        session.query(Message)
        .filter(Message.chat_id == chat.id)
        .order_by(Message.sent_at.desc())
        .first()
        )

        print("messagee", message)
        if message:
            chat_obj["last_message"] = {
                "text": message.text,
                "sent_at": message.sent_at,
            }

            data.append(chat_obj)


    print(data)
    return data


def get_messages_between_users(session: Session, user1_id, user2_id):
    # Найдем id чата, где оба пользователя являются участниками
    chat_ids_subq = (
        session.query(ChatParticipant.chat_id)
        .filter(ChatParticipant.user_id.in_([user1_id, user2_id]))
        .group_by(ChatParticipant.chat_id)
        .having(func.count(ChatParticipant.user_id) == 2)
        .subquery()
    )

    # Получим все сообщения из таких чатов
    messages = (
        session.query(Message)
        .filter(Message.chat_id.in_(chat_ids_subq))
        .order_by(Message.sent_at)
        .all()
    )

    return messages


# def check_for_chat(this_user: User, other_user: User) -> bool:
#     """
#     Check if this users have chat:
#         1. Take list of chat participants of this_user
#         2. Iterate throug list and chat all chat if those chats have other_user as participant
#     """
#     result = False
#     while not result:
#         for participant in this_user.chat_list:
#             participant: ChatParticipant
#             chat: Chat = participant.chat
#             chat_patricipants_list: list[ChatParticipant] = chat.participants
#             for patricipant in chat_patricipants_list:
#                 if patricipant == other_user:
#                     # means they have chat
#                     result = True
#                 else:
#                     # means they DO NOT have chat, then make it
#                     continue
#         break
#     return result

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    When client opens conncection it sends json with access_token,
    then server authenticates it.
    If Authnticated

    If not Authnticated closes connection
    """
    await websocket.accept()
    # await websocket.send_json({"info": "You connected to the server"})

    # Authenticate connection
    data: dict= await websocket.receive_json()
    if auth(data.get("access_token")):
        try:
            # await websocket.send_text(f"You authenticated")
            access_token = decode(data.get("access_token"))
            await manager.add(access_token.get("user_id"), websocket)  # User Authenticated and added to the all connection dict
            # await websocket.send_text(f"All connections: {manager.active_connections}")
            this_user_id = access_token.get("user_id")
            
            while True:
                print("loop started", flush=True)
                message: dict = await websocket.receive_json()
                other_user_id = message["selectedUserId"]

                with sessionLocal() as session:
                    session: Session

                    this_user: User = session.query(User).filter_by(id=this_user_id).first()
                    other_user = session.query(User).filter_by(id=other_user_id).first()
                    """
                    Check if this users have chat:
                        1. Take list of chat participants of this_user
                        2. Iterate throug list and chat all chat if those chats have other_user as participant
                    """
                    chat_exists = check_for_chat(session, this_user_id, other_user_id)
                    print(chat_exists, "EXISTS?")
                    if chat_exists:
                        # if chat exists between those users    new_message = Message(new_chat.id, this_user, message.get("message"))

                        chat = get_chat(session, this_user.id, other_user_id)
                        new_message = Message(chat.id, this_user.id, message.get("message"))
                        other_user_websocket = manager.active_connections.get(other_user_id)
                        try:
                            print(manager.active_connections, "active connctions")
                            session.add(new_message)
                            session.commit()
                            session.refresh(new_message)
                            # other_user_websocket.send_text("hello new message")
                            # This sent to the receiver
                            data = {
                                "message_obj": new_message.to_dict(),
                                "sent_at": str(new_message.sent_at),
                                "sender_id": this_user_id,
                                "sender_username": this_user.username,
                                "receiver_id": other_user_id,
                                "receiver_username": session.query(User).filter_by(id=other_user_id).first().username,
                            }
                            await manager.send_personal_message(data, manager.active_connections.get(other_user_id))
                            # {
                            #     "info": "message sent",
                            #     "message_obj": new_message.to_dict(),
                            #     # "is_own_message": True,
                            #     "sender_id": this_user.id,
                            #     "receiver_id": other_user_id,
                            #     "receiver_username": session.query(User).filter_by(id=other_user_id).first().username,

                            #     "data": str(manager.active_connections)
                            # }
                            # This sent to the sender
                            await websocket.send_json(data)
                        except Exception as e:
                            print(f"Error here: {str(e)}")

                    else:
                        # if chat NOT exists between those users, then we create itr
                        try:
                            new_chat = Chat()
                        
                            session.add(new_chat)
                            session.commit()
                            session.refresh(new_chat)

                            this_user_CP = ChatParticipant(chat_id=new_chat.id, user_id=this_user.id)
                            other_user_CP = ChatParticipant(chat_id=new_chat.id, user_id=other_user.id)

                            session.add(this_user_CP)
                            session.add(other_user_CP)
                            
                            session.commit()

                            # Chat created, then send message itself
                            new_message = Message(new_chat.id, this_user.id, message.get("message"))
                            
                            session.add(new_message)
                            session.commit()
                            session.refresh(new_message)

                            data = {
                                "message_obj": new_message.to_dict(),
                                "sent_at": str(new_message.sent_at),
                                "sender_id": this_user_id,
                                "sender_username": this_user.username,
                                "receiver_id": other_user_id,
                                "receiver_username": session.query(User).filter_by(id=other_user_id).first().username,
                            }
                            await manager.send_personal_message(data, manager.active_connections.get(other_user_id))


                            print(this_user.chat_list)

                        except Exception as e:
                            print(f"Exeprion in creatin new chat: {e}")




                   
        except WebSocketDisconnect as e:
            # delete this websocket from pool
            websocket.close()
            manager.disconnect(websocket)
        except Exception as e:
            print(f"Error: Unknow exception occured in chat-service /ws endpoint: {str(e)}")
    
    else:
        await websocket.send_text(f"You NOT authenticated")
        websocket.close()

@app.get("/load-chats")
async def load_chats(request: Request):
    # TODO make token extraction and authentication like in other endpoints
    authenticate_header: str = request.headers.get("Authenticate")  #  "Bearer token.abc"
    if authenticate_header:
        authenticate_header_parts = authenticate_header.split(" ")  # ["Bearer", "token.abc"]
        if authenticate_header_parts[0] == "Bearer" and auth(authenticate_header_parts[1]):
            # If user authnticated
            token_data =  decode(authenticate_header_parts[1])
            this_user_id = token_data.get("user_id")

            with sessionLocal() as session:
                session: Session
                
                # user = session.get(User, token_data.get("user_id"))

                result = super_func(session=session, user_id=this_user_id)

                return result

            return   # Returns true or false
        else: 
            return JSONResponse(content={"custom_msg": "User unauthenticated."}, status_code=401)
    else:
        return JSONResponse(content={"custom_msg": "No header provided"}, status_code=400)


@app.post("/find-user")
async def find_user(request: Request):
    users_access_token = extract_access_token_from_header(  # Get user's access token
        request.headers.get("Authenticate")
    )

    if auth(users_access_token):  #  Check if token authentocated, if not return - 401 Unauthorized
        body: dict = await request.json()
        if username:= body.get("username"):
            # If username passed in body
            with sessionLocal() as session:
                session: Session
                if user:= session.query(User).filter_by(username=username).first():
                    # If user found in DB do stuff
                        
                    data = {
                        "username": user.username,
                        "user_id": user.id,
                        "messages": []
                    }
                    return data
                else:
                    return JSONResponse(content="User not found", status_code=404)
        
        return body
    else:
        return JSONResponse(content="Unauthorized", status_code=401)




@app.post("/new-chat")
async def new_chat(request: Request):
    users_access_token = extract_access_token_from_header(  # Get user's access token
        request.headers.get("Authenticate")
    )

    if auth(users_access_token):  #  Check if token authentocated, if not return - 401 Unauthorized

        access_token_data: dict = decode(users_access_token)
        body: dict = await request.json()

        with sessionLocal() as session:
            session: Session
            # Check if user clinent tries to find exists
            if other_user:= session.query(User).filter_by(username=body.get("username")).first():
                this_user = session.query(User).filter_by(id=access_token_data.get("user_id")).first()

                if this_user == other_user:
                    # if user tries to find himself returnt not found
                    return JSONResponse(content="User not found.", status_code=404)
                
                """
                To create new chat:
                    1. Create Chat
                    2. Do ChatParticipants for both users
                    3. Connect ChatParticipants to Chat
                """
                try:
                    new_chat = Chat()
                    
                    session.add(new_chat)
                    session.commit()
                    session.refresh(new_chat)

                    this_user_CP = ChatParticipant(chat_id=new_chat.id, user_id=this_user.id)
                    other_user_CP = ChatParticipant(chat_id=new_chat.id, user_id=other_user.id)

                    session.add(this_user_CP)
                    session.add(other_user_CP)
                    
                    session.commit()

                    return JSONResponse("Chat successfuly created.")
                except Exception as e:
                    raise Exception(f"Unknown error occured at creating new chat: {str(e)}")

            else:
                return JSONResponse(content="User not found.", status_code=404)
        
            
        return {"data": decode(users_access_token), "data2": body}
    else:
        JSONResponse(content="Create new chat action Unauthorized.", status_code=401)

@app.post("/load-messages")
async def load_messages(request: Request):
    users_access_token = extract_access_token_from_header(  # Get user's access token
        request.headers.get("Authenticate")
    )

    access_token = decode(users_access_token)

    if auth(users_access_token):  #  Check if token authenticated, if not return - 401 Unauthorized
        body: dict = await request.json()
        chatter_id = body.get("chatter_id")
        user_id = access_token.get("user_id")
        with sessionLocal() as session:
            session: Session
            messages_list = get_messages_between_users(session, user_id, chatter_id)
            return messages_list
        # return {
        #     "chatter_id": chatter_id,
        #     "user_id": user_id
        # }
        
        
        
        
        # return body

        




    # await websocket.send_text(f"Message text was: hello world")
    


        

# @app.get("/load-chats")
# async def load_chats(request: Request):
#     authenticate_header: str = request.headers.get("Authenticate")  #  "Bearer token.abc"
#     print(authenticate_header)
#     if authenticate_header:
#         authenticate_header_parts = authenticate_header.split(" ")  # ["Bearer", "token.abc"]
#         if authenticate_header_parts[0] == "Bearer" and auth(authenticate_header_parts[1]):
#             # If user authnticated
#             token_data =  decode(authenticate_header_parts[1])

#             with sessionLocal() as session:
#                 session: Session
#                 # session.begin()
#                 user = session.get(User, token_data.get("user_id"))
#                 user.chat_list
#                 return str(user.chat_list)

#             return   # Returns true or false
#         else: 
#             return JSONResponse(content={"custom_msg": "User unauthenticated."}, status_code=401)
#     else:
#         return JSONResponse(content={"custom_msg": "No header provided"}, status_code=400)



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8082, reload=True)

# ===================================================

# from fastapi import FastAPI
# from fastapi import WebSocket

# import uvicorn
# import redis


# redis_db = redis.Redis(host="redis", port=6379, decode_responses=True)


# # This function launches before fastapi instace runes

# app = FastAPI( root_path="/api/chat-service")  # Fastapi app initialization with its user-service default path

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         # await websocket.
#         await websocket.send_text(f"Message text was: {data}")




