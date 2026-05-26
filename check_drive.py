import sys; sys.path.insert(0, ".")
from utils.drive_sync import _get_creds, _req, _DRIVE_FILES
import urllib.parse

creds = _get_creds()

def listar(pasta_id, indent=0):
    q = f"'{pasta_id}' in parents and trashed=false"
    url = _DRIVE_FILES + "?" + urllib.parse.urlencode({"q": q, "fields": "files(id,name,mimeType,createdTime)", "orderBy": "createdTime"})
    files = _req(url, creds).get("files", [])
    for f in files:
        tipo = "[pasta]" if "folder" in f["mimeType"] else "[arq]"
        print(" " * indent + f"{tipo} {f['name']}  criado={f['createdTime'][:19]}  ({f['id']})")
        if "folder" in f["mimeType"]:
            listar(f["id"], indent + 4)

print("internacao/")
# ID da pasta internacao encontrada antes
listar("1y1q3HR5zsBtxafjDXmT10tCi8Sy7qU5x")
