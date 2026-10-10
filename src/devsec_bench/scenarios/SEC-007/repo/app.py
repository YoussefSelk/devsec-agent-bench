def delete_account(request, store):
    return store.delete(request["account_id"])
