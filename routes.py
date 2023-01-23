from blog_system import app
from pydantic import BaseModel
from fastapi.responses import JSONResponse


import psycopg2

try:
    conn = psycopg2.connect(database="blog_system", user = "postgres", host = "127.0.0.1", port = "5432")
except Exception as e:
    print(e)



class blog_title(BaseModel):
    title: str
    start_para : int = None

class paragraph(BaseModel):
    paragraph : str
    after : int = None
    

@app.post("/createblog/")
async def createblog(blog_title:blog_title):
    cur = conn.cursor()
    print(blog_title)
    cur.execute(f"Insert into blog_title(title) values ('{blog_title.title}')")
    conn.commit()
    return JSONResponse(content={"status": "success"}, status_code=201)


@app.post("/blog/{blog_id}/add_para/")
async def add_paragraph(blog_id : int , paragraph: paragraph):
    cur = conn.cursor()
    if paragraph.after is not None:
        cur.execute(f"select next_para_id from para_table where id = {paragraph.after}")
        row = cur.fetchone()
        next_para_id = row[0]
        if next_para_id is not None:
            cur.execute(f"Insert into para_table (para_text) values ('{paragraph.paragraph}') returning id")
            new_row_id = cur.fetchone()[0]
            cur.execute(f"Update para_table set next_para_id = {new_row_id} where id = {paragraph.after}")
            cur.execute(f"Update para_table set next_para_id = {next_para_id} where id = {new_row_id}")
            conn.commit()
            return {"status" : "success"}


    cur.execute(f"select start_para_id from blog_title where id = {blog_id}")
    row = cur.fetchone()
    if row[0] is None:
        cur.execute(f"Insert into para_table (para_text) values ('{paragraph.paragraph}') returning id")
        conn.commit()
        cur.execute(f"UPDATE blog_title SET start_para_id = {cur.fetchone()[0]} WHERE id = {blog_id}")
        conn.commit()
        return {"status":"success"}
    else:
        id = 0
        next = row[0]
        while next is not None:
            cur.execute(f"select id, next_para_id from para_table where id = {next}")
            row = cur.fetchone()
            print(row)
            id, next = row
        cur.execute(f"Insert into para_table (para_text) values ('{paragraph.paragraph}') returning id")
        conn.commit()
        cur.execute(f"Update para_table set next_para_id = {cur.fetchone()[0]} where id = {id} ")
        conn.commit()
        return {"status":"success"}


@app.delete("/paragraph/{para_id}/")
async def delete_paragraph(para_id : int):
    cur = conn.cursor()
   
    cur.execute(f"select next_para_id from para_table where id = {para_id}")
    next_para_id = cur.fetchone()[0]
    if next_para_id is None:
        cur.execute(f"delete from para_table where id = {para_id}")
        conn.commit()
        return {"status":"success"}
    else:
        cur.execute(f"select * from para_table where next_para_id = {para_id}")
        row = cur.fetchone()
        if row is None:
            cur.execute(f"select next_para_id from para_table where id = {para_id}")
            next_para_id = cur.fetchone()[0]
            cur.execute(f"update blog_title set start_para_id = {next_para_id} where start_para_id = {para_id}")
            cur.execute(f"delete from para_table where id = {para_id}")
            conn.commit()
            return {"status": "success"}
        else:
            cur.execute(f"select next_para_id from para_table where id = {para_id}")
            next_para_id = cur.fetchone()[0]
            cur.execute(f"update para_table set next_para_id = {next_para_id} where next_para_id = {para_id}")
            cur.execute(f"delete from para_table where id = {para_id}")
            conn.commit()
            return {"status":"success"}

@app.get("/blog/{blog_id}/")
async def get_blog_details(blog_id : int):
    cur = conn.cursor()
    paragraphs = []
    cur.execute(f"select id , title, start_para_id from blog_title where id = {blog_id}")
    row = cur.fetchone()
    print(row)
    id, title, start_para_id = row
    if start_para_id is not None:
        cur.execute(f"select id, para_text, next_para_id from para_table where id = {start_para_id} ")
        row = cur.fetchone()
        id , para_text, next_para_id = row
        while next_para_id is not None:
            para_dict = {
                "id" : id,
                "paragraph" : para_text,
                "next_para_id" : next_para_id 
            }
            paragraphs.append(para_dict)
            cur.execute(f"select id, para_text, next_para_id from para_table where id = {next_para_id}")
            row = cur.fetchone()
            id , para_text, next_para_id = row
        para_dict = {
            "id" : id,
            "paragraph" : para_text,
            "next_para_id" : next_para_id 
        }
        paragraphs.append(para_dict)
        data = {
            "id" : blog_id,
            "title" : title,
            "paragraphs" : paragraphs
        }
        return data
    else:
        return {
            "id" : id,
            "title" : title,
            "start_para_id" :  start_para_id
        }


@app.delete("/blog/{blog_id}/")
def delete_blog(blog_id : int):
    cur = conn.cursor()
    cur.execute(f"select start_para_id from blog_title where id = {blog_id}")
    start_para_id = cur.fetchone()[0]
    if start_para_id is not None:
        cur.execute(f"select next_para_id from para_table where id = {start_para_id}")
        next_para_id = cur.fetchone()[0]
        cur.execute(f"delete from para_table where id = {start_para_id}")
        conn.commit()
        while next_para_id is not None:
            delete_id = next_para_id
            cur.execute(f"select next_para_id from para_table where id = {next_para_id}")
            next_para_id = cur.fetchone()[0]
            cur.execute(f"delete from para_table where id = {delete_id}")
            conn.commit()
        cur.execute(f"delete from blog_title where id = {blog_id}")
        conn.commit()
        return {"status" :"success"}
    else:
        cur.execute(f"delete from blog_title where id = {blog_id}")
        conn.commit()
        return {"status" :"success"}

@app.put("/paragraph/switch/{para_id_1}/{para_id_2}/")
async def switch(para_id_1: int, para_id_2 : int):
    cur = conn.cursor()
    cur.execute(f"select para_text from para_table where id = {para_id_1}")
    para_text_1 = cur.fetchone()[0]
    cur.execute(f"select para_text from para_table where id = {para_id_2}")
    para_text_2 = cur.fetchone()[0]

    cur.execute(f"Update para_table set para_text = '{para_text_2}' where id = {para_id_1}")
    cur.execute(f"Update para_table set para_text = '{para_text_1}'  where id = {para_id_2}")
    conn.commit()
    return {"status": "success"}

class comment(BaseModel):
    comment : str


@app.post("/para/{para_id}/comment/")
def add_comment(para_id : int , comment : comment):
    cur = conn.cursor()
    cur.execute(f"Insert into comment_table (para_id, comment) values ('{para_id}', '{comment.comment}')")
    conn.commit()
    return {"status":"success"}
        
            
        


    
    
