from aiohttp import web
from config import Config

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({
        "status": "online",
        "bot": "VC Story Finder Bot",
        "server": "Render Keep-Alive Active",
        "port": Config.PORT
    })

async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app
  
