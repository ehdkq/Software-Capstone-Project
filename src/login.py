from fastapi import FastAPI
from src.db import supabase

app = FastAPI()

# pull from db: response = supabase.table("TABLE_NAME").select("* (ALL)").execute()
# write to db: response = supabase.table("TABLE_NAME").insert(data - typically a dict).execute()
# update db: response = supabase.table("TABLE_NAME")\.update({"column name": "column value"})\.eq("value", what_value_equals)\.execute()
# delete from db: response = supabase.table("TABLE_NAME")\.delete()\.eq("value", what value equals)\.execute()
# return response

# TODO
@app.get("/login")
def get_users():
    response = supabase.table("customers").select("*").execute()
    return response.data

print(get_users())