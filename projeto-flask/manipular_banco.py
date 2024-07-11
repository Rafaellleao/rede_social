from pacote import db, app
from pacote.models import User, Post


with app.app_context():
    posts = Post.query.all()
            
    for post in posts:
        print(post.title, post.author.username)


