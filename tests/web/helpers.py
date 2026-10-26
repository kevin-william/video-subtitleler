import json
from email.parser import BytesParser
from email.policy import default


def multipart_values(body):
    boundary = body.split(b"\r\n", 1)[0][2:]
    message = BytesParser(policy=default).parsebytes(b"Content-Type: multipart/form-data; boundary=" + boundary + b"\r\n\r\n" + body)
    return {part.get_param("name", header="content-disposition"): part.get_payload(decode=True) for part in message.iter_parts()}


def custom_style(body):
    return json.loads(multipart_values(body)["custom_style"])
