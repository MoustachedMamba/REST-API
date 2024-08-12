import json
import math
from fastapi import FastAPI
from fastapi import Response, Request
from sqlalchemy import select, insert, update
from src.models import ENTITY_DICT, session
from src.utils import send_mail


app = FastAPI()
ERROR_RESPONSE = json.dumps({"data": "Error"})


@app.get("/api/{model}")
async def get_object_collection(model: str, limit: int = 5, page: int = 1):
    result = ERROR_RESPONSE
    try:
        if model not in ENTITY_DICT.keys():
            return ERROR_RESPONSE
        query = session.query(ENTITY_DICT[model]).filter().limit(limit).offset((page - 1) * limit)
        query_result = query.all()
        data = []
        for row in query_result:
            data.append(json.loads(row.convert_to_json()))
        row_count = session.query(ENTITY_DICT[model]).filter().count()
        pagination = {
            "current_page": page,
            "last_page": math.ceil(row_count / limit),
            "per_page": limit,
            "total": row_count
        }

        if page > math.ceil(row_count / limit):
            raise ValueError("current page is greater then last page!")
        result = json.dumps({"data": data, "meta": pagination})
    except Exception as error:
        result = json.dumps({"Error": str(error)})
        session.rollback()
    finally:
        return Response(content=result, media_type="application/json")


@app.get("/api/{model}/{uid}")
async def get_object_by_id(model: str, uid: int):
    result = ERROR_RESPONSE
    try:
        if model not in ENTITY_DICT.keys():
            return ERROR_RESPONSE
        statement = select(ENTITY_DICT[model]).where(ENTITY_DICT[model].id == uid)
        query_result = session.execute(statement)
        session.commit()
        result = query_result.one()[0].convert_to_json()
    except Exception as error:
        result = json.dumps({"Error": str(error)})
        session.rollback()
    finally:
        return Response(content=result, media_type="application/json")


@app.post("/api/{model}")
async def post_object(model: str, data: Request):
    result = ERROR_RESPONSE
    try:
        if model not in ENTITY_DICT.keys():
            raise Exception
        data_dict = await data.json()
        new_object = ENTITY_DICT[model](**data_dict)
        session.add(new_object)
        session.commit()
        result = new_object.convert_to_json()
    except Exception as error:
        result = json.dumps({"Error": str(error)})
        session.rollback()
    finally:
        return Response(content=result, media_type="application/json")


@app.post("/api/send_mail/{uid}")
async def post_mail(uid: int, data: Request):
    result = ERROR_RESPONSE
    try:
        data_dict = await data.json()
        statement = select(ENTITY_DICT["users"]).where(ENTITY_DICT["users"].id == uid)
        query_result = session.execute(statement)
        session.commit()
        address = query_result.one()[0].email
        send_mail(address, data_dict["subject"], data_dict["content"])
        result = json.dumps({"Mail": "Sent"})
    except Exception as error:
        result = json.dumps({"Error": error})
        session.rollback()
    finally:
        return Response(content=result, media_type="application/json")


@app.put("/api/{model}/{uid}")
async def put_object(model: str, uid: int, data: Request):
    result = ERROR_RESPONSE
    try:
        if model not in ENTITY_DICT.keys():
            raise Exception
        object_to_update = session.get(ENTITY_DICT[model], uid)
        data_dict = await data.json()
        for key in data_dict.keys():
            setattr(object_to_update, key, data_dict[key])
        session.commit()
        result = object_to_update.convert_to_json()
    except Exception as error:
        result = json.dumps({"Error": str(error)})
        session.rollback()
    finally:
        return Response(content=result, media_type="application/json")


@app.delete("/api/{model}/{uid}")
async def delete_object(model: str, uid: int):
    result = json.dumps({})
    try:
        if model not in ENTITY_DICT.keys():
            return ERROR_RESPONSE
        object_to_delete = session.get(ENTITY_DICT[model], uid)
        session.delete(object_to_delete)
        session.commit()
        result = json.dumps({"data": "ok"})
    except Exception as error:
        result = json.dumps({"Error": str(error)})
        session.rollback()
    finally:
        return Response(content=result, media_type="application/json")
