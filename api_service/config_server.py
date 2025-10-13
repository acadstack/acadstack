from quart import Quart, request
from quart.helpers import send_file
app = Quart(__name__)


@app.route("/load_cfg", methods=['POST'])
async def load_cfg():
    form = await request.form
    un = form['username']
    return await send_file("config.json", mimetype="application/json")


if __name__ == "__main__":
    app.run(host="localhost", port=9909)
