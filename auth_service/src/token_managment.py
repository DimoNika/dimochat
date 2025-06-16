from datetime import datetime, timedelta, timezone
from jose import jwt, jws, jwe
from jose.exceptions import JWSError

SECRET_KEY = "JWT_SECRET_KEYJWT_SECRET_KEYJWT_SECRET_KEY1"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 0.8  # 15 mins
REFRESH_TOKEN_EXPIRE_MINUTES = 72000  # 50 days



def auth(token):
    """
    Function that verifies integrity of any JWT.
    Returns bool
    """
    try:
        jws.verify(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWSError:
        return False
    except Exception as e:
        raise Exception(f"Something happened in verifying JWT: {str(e)}")
    else:
        return True

def create_access_token(data: dict):
    """
    ### Access token
    Takes data as argument, adds expire date and encodes to JWT.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return token


def create_refresh_token(data: dict):
    """
    ### Refresh token
    Takes data as argument, adds expire date and encodes to JWT
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token
    
    

def decode(token: str):
    """
    Function that extracts paload, returns dict
    """
    try:
        
        payload = jwt.decode(token, key=SECRET_KEY, options={"verify_signature": False})
        return payload
    except Exception as e:
        print("Couldnt decode JWT:", str(e))
        return False


