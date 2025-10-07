# routers/auth.py
import os
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from sqlalchemy.orm import Session
from database import get_db
from models.user import User

router = APIRouter()

# Initialize Firebase Admin - support passing service account JSON in env (RENDER safe)


def _init_firebase():
    if firebase_admin._apps:
        return
    json_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    json_path = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if json_env:
        # write to temp file
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
def verify_token(payload: TokenIn, db: Session = Depends(get_db)):
    try:
        decoded = firebase_auth.verify_id_token(payload.token)
        uid = decoded["uid"]
        email = decoded.get("email")
        name = decoded.get("name", "")
        # create or fetch user
        user = db.query(User).filter_by(firebase_uid=uid).first()
        if not user:
            user = User(name=name, email=email, firebase_uid=uid)
            db.add(user)
            db.commit()
            db.refresh(user)
        return {"status": "ok", "user": {"id": user.id, "email": user.email, "name": user.name}}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# dependency usable by other routers


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Missing Authorization header")
    try:
        token = authorization.split("Bearer ")[1]
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded["uid"]
        user = db.query(User).filter_by(firebase_uid=uid).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
