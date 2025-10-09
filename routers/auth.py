import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from datetime import datetime
from bson.objectid import ObjectId


load_dotenv()

router = APIRouter()


def _init_firebase():
    if firebase_admin._apps:
        return
    json_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    json_path = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if json_env:

        fp = "/tmp/firebase_service_account.json"
        with open(fp, "w") as f:
            f.write(json_env)
        cred = credentials.Certificate(fp)
    elif json_path:
        cred = credentials.Certificate(json_path)
    else:
        raise RuntimeError(
            "Set FIREBASE_SERVICE_ACCOUNT_JSON (content) or FIREBASE_CREDENTIALS_JSON (path)")
    firebase_admin.initialize_app(cred)


_init_firebase()


class TokenIn(BaseModel):
    token: str


@router.post("/verify")
async def verify_token(payload: TokenIn, request: Request):
    try:
        decoded = firebase_auth.verify_id_token(payload.token)
        uid = decoded["uid"]
        email = decoded.get("email")
        name = decoded.get("name", "")

        user = await request.app.db.users.find_one({"uid": uid})

        if not user:

            user_data = {
                "uid": uid,
                "email": email,
                "display_name": name,
                "created_at": datetime.utcnow()
            }
            await request.app.db.users.insert_one(user_data)
            user = user_data

        return {"uid": uid, "valid": True, "user": {"id": str(user["_id"]), "email": user["email"], "name": user["display_name"]}}
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request, authorization: str = Header(None)):
    print(
        f"[DEBUG] get_current_user called, authorization header present: {bool(authorization)}")
    if not authorization:
        print("[DEBUG] No authorization header")
        raise HTTPException(
            status_code=401, detail="Missing Authorization header")
    try:
        token = authorization.split("Bearer ")[1]
        print(f"[DEBUG] Token extracted, length: {len(token)}\n")
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded["uid"]
        print(f"[DEBUG] Token verified, uid: {uid}\n")

        user = await request.app.db.users.find_one({"uid": uid})
        if not user:
            print(f"[DEBUG] User not found in database for uid: {uid}\n")
            raise HTTPException(status_code=401, detail="User not found")
        print(f"[DEBUG] User found: {user['uid']}\n")

        class CurrentUser(BaseModel):
            id: str
            email: str
            display_name: str

            class Config:
                arbitrary_types_allowed = True

        return CurrentUser(id=str(user["_id"]), email=user["email"], display_name=user["display_name"])
    except HTTPException:
        raise
    except Exception as e:
        print(
            f"[DEBUG] Token verification failed: {type(e).__name__}: {str(e)}\n")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
