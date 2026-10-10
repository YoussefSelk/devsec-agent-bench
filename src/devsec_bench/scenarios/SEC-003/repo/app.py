def create_user(request):
    age = request["age"]
    return {"age": age}
