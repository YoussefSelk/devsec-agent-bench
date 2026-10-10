from pathlib import Path
def download(request):
    return (Path("uploads") / request["filename"]).read_text()
