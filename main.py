from fastapi import FastAPI
from fastapi import Response
from fastapi import Query, Path
from orm import *


app = FastAPI()


@app.get("/api/{model}")
async def obj_collection(model: str, limit: int = Query(ge=0), page: int = Query(ge=0)):
    result = get_collection(model, limit, page)
    return Response(content=result, media_type="application/json")


@app.get("/api/{model}/{uid}")
async def obj_by_id(model: str, uid: int):
    obj = entity_dict[model]()
    obj.load_obj(uid=uid)
    result = obj.obj2json()
    print(result)
    return Response(content=result, media_type="application/json")


