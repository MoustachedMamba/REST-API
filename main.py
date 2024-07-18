import json
import uvicorn

from fastapi import FastAPI
from fastapi import Response, Query, Path, Request, Depends
from orm import *
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Union

app = FastAPI()
client = TestClient(app)


class QueryParams(BaseModel):
    dynamic: dict


async def query_params(request: Request, model: str, limit: int, page: int):
    dynamic_params = {}
    for k in request.query_params.keys():
        dynamic_params[k] = request.query_params[k]
    return {"model": model, "limit": limit, "page": page, "dynamic": dynamic_params}


@app.get("/api/{model}")
async def obj_collection(model: str, limit: int, page: int, params: QueryParams = Depends(query_params)):
    result = get_collection(model, limit, page, params["dynamic"])
    return Response(content=result, media_type="application/json")


@app.get("/api/{model}/{uid}")
async def obj_by_id(model: str, uid: int):
    obj_to_get = entity_dict[model]()
    if obj_to_get.get_obj(uid=uid):
        obj_to_get.load_obj(uid=uid)
        result = obj_to_get.obj2json()
    else:
        result = json.dumps({"data": "fail"})
    return Response(content=result, media_type="application/json")


@app.post("/api/{model}")
async def obj_post(model: str, data: Request):
    obj_to_post = entity_dict[model]()
    data_fields = obj_to_post.fields
    d = json.loads(await data.json())
    for k in data_fields:
        obj_to_post.data[k] = d[k]
    new_id = obj_to_post.insert_obj()
    if new_id:
        obj_to_post.load_obj(uid=new_id)
        result = obj_to_post.obj2json()
    else:
        result = json.dumps({"data": "fail"})
    return Response(content=result, media_type="application/json")


@app.put("/api/{model}/{uid}")
async def obj_change(model: str, uid: int, data: Request):
    obj_to_change = entity_dict[model]()
    print(2, obj_to_change.data)
    if obj_to_change.get_obj(uid=uid):
        print(3, obj_to_change.data)
        obj_to_change.load_obj(uid)
        print(4, obj_to_change.data)
        change = json.loads(await data.json())
        print(5, obj_to_change.data)
        for k in change.keys():
            if k in obj_to_change.fields:
                print(6, obj_to_change.data)
                obj_to_change.data[k] = change[k]
                print(7, obj_to_change.data)
        final = obj_to_change.push_update()
        print(8, obj_to_change.data)
        if final:
            print(9, obj_to_change.data)
            result = obj_to_change.obj2json()
        else:
            print(10, obj_to_change.data)
            result = json.dumps({"data": "Nothing happened"})
    else:
        result = json.dumps({"data": "failed"})
    return Response(content=result, media_type="application/json")


@app.delete("/api/{model}/{uid}")
async def obj_delete(model: str, uid: int):
    obj_to_delete = entity_dict[model]()
    if obj_to_delete.delete_obj(uid=uid):
        result = json.dumps({"data": "ok"})
    else:
        result = json.dumps({"data": "failed"})
    return Response(content=result, media_type="application/json")


@app.post("/api/email/{uid}")
async def send_mail(uid: int, data: Request):
    recipient = User()
    recipient.load_obj(uid=uid)
    d = json.loads(await data.json())
    try:
        if recipient.send_email(d["mail_subject"], d["mail_content"]):
            result = await data.json()
        else:
            result = json.dumps({"data": "failed"})
    except KeyError as err:
        print(err)
        result = json.dumps({"data": "failed"})
    except Exception as err:
        print(err)
        result = json.dumps({"data": "failed"})
    return Response(content=result, media_type="application/json")


# TESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTINGTESTING
@app.get("/test/post/user/{name}")  # OK
async def post_user(name: str):
    new_data = User()
    new_data.data["email"] = f"{name}@mmm.ru"
    new_data.data["password"] = f"{name}"
    new_data.data["is_logged"] = False
    new_data.data["is_admin"] = False
    result = client.post('/api/users', json=new_data.obj2json())
    return result.json()


@app.get("/test/post/articles/{uid}/{name}")  # OK
async def post_article(uid: int, name: str):
    new_data = Article()
    new_data.data["user_id"] = f"{uid}"
    new_data.data["name"] = f"{name}"
    new_data.data["article"] = "A chair is a type of seat, typically designed for one person and consisting of one or " \
                               "more legs, a flat or slightly angled seat and a back-rest. It may be made of wood, " \
                               "metal, or synthetic materials, and may be padded or upholstered in various colors and " \
                               "fabrics. "
    result = client.post('/api/articles', json=new_data.obj2json())
    return result.json()


@app.get("/test/post/videos/{uid}/{name}")  # OK
async def post_video(uid: int, name: str):
    new_data = Video()
    new_data.data["user_id"] = f"{uid}"
    new_data.data["name"] = f"{name}"
    new_data.data["url"] = "https://www.youtube.com/watch?v=Wp9pzKbENQk"
    result = client.post('/api/videos', json=new_data.obj2json())
    return result.json()


@app.get("/test/post/comments/{uid}/{sid}")  # OK
async def post_comment(uid: int, sid: int):
    new_data = Comment()
    new_data.data["user_id"] = f"{uid}"
    new_data.data["comment"] = f"Very long comment blablabla."
    new_data.data["media_type"] = f"vid"
    new_data.data["media_id"] = f"{sid}"
    result = client.post('/api/comments', json=new_data.obj2json())
    return result.json()


@app.get("/test/delete/{model}/{uid}")  # OK
async def test_delete(model: str, uid: int):
    print("here")
    result = client.delete(f'/api/{model}/{uid}')
    print("there")
    return result.json()


@app.get("/test/put/{model}/{uid}")
async def test_put(model: str, uid: int):
    if model == "users":
        new_data = json.dumps({"email": "ivan.govnov@yandex.ru"})  # OK
    elif model == "articles":
        new_data = json.dumps({"name": "Actually, I don't like chairs."})  # OK
    elif model == "videos":
        new_data = json.dumps({"name": "Actually, dungeon synth sucks!"})  # OK
    else:
        new_data = json.dumps({"comment": "GOVNO! OTPISKA!"})  # OK
    result = client.put(f"api/{model}/{uid}", json=new_data)
    return result.json()


@app.get("/test/email/{uid}")
async def test_mail(uid: int):  # Works
    mail_data = json.dumps({"mail_subject": "My greetings.", "mail_content": "Hello, my friend."})
    result = client.post(f"api/email/{uid}", json=mail_data)
    return result.json()
