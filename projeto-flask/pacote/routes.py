from flask import render_template, request, redirect, url_for, flash, abort
from pacote import app, db, bcrypt, login_manager, mail
from datetime import datetime, timedelta
from pacote.forms import (RegistrationForm, LoginForm, PostForm,
                          UpdateAccountForm, RequestResetForm, ResetPasswordForm)
from pacote.models import User, Post
from datetime import datetime
from sqlalchemy import desc
from flask_login import login_required, current_user, login_user, logout_user
import os
import secrets
from PIL import Image
from flask_mail import Message
import requests


def time_elapsed_since(creation_time):
    now = datetime.now()
    delta = now - creation_time
    
    seconds = delta.total_seconds()
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    weeks = days // 7
    months = days // 30  # Aproximado
    years = days // 365  # Aproximado
    
    if seconds < 60:
        elapsed_time_str = "Agora mesmo"
    elif minutes < 60:
        elapsed_time_str = f"Há {int(minutes)} {'minuto' if int(minutes) == 1 else 'minutos'}"
    elif hours < 24:
        elapsed_time_str = f"Há {int(hours)} {'hora' if int(hours) == 1 else 'horas'}"
    elif days < 7:
        elapsed_time_str = f"Há {int(days)} {'dia' if int(days) == 1 else 'dias'}"
    elif weeks < 4:
        elapsed_time_str = f"Há {int(weeks)} {'semana' if int(weeks) == 1 else 'semanas'}"
    elif months < 12:
        elapsed_time_str = f"Há {int(months)} {'mês' if int(months) == 1 else 'meses'}"
    else:
        elapsed_time_str = f"Há {int(years)} {'ano' if int(years) == 1 else 'anos'}"
    
    return elapsed_time_str



resposta = requests.get('https://economia.awesomeapi.com.br/last/USD')
dictionario = resposta.json()
dolar = dictionario['USDBRL']['bid']



@app.route('/')
@app.route('/home')
def home():
    with app.app_context():
        per_page = 5
        page = request.args.get('page', 1, type=int)
        posts =  Post.query.order_by(desc(Post.date_create)).paginate(page=page, per_page=per_page, error_out=False)
        return render_template('home.html', posts=posts, time_elapsed_since=time_elapsed_since, dolar=dolar[:-1])
    


@app.route('/about')
def about():
    with app.app_context():
        posts = Post.query.all()
        if current_user.is_authenticated:
            tamanho = len(current_user.posts)
        else:
            tamanho = None  # ou qualquer valor padrão que faça sentido no seu contexto
    return render_template('about.html', title='about', posts=posts, tamanho=tamanho, dolar=dolar[:-1])


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if current_user.is_authenticated:
        flash(f'{current_user.username} Voce ja esta logado e resgristrado pode postar', 'info')
        return redirect(url_for('postagem'))
    if form.validate_on_submit():
        user = User.query.filter_by(email= form.email.data).first()
        if user is None:
            senha_criptografada = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, email=form.email.data, password=senha_criptografada)
            db.session.add(user)
            db.session.commit() 
            flash(f'Account created for {user.username} Success!', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Username e Email ja exiti por favor escolha outros', 'info')
            return redirect(url_for('register')) 
    return render_template('register.html', legend='Register', form=form, dolar=dolar[:-1])

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        flash(f'{current_user.username} voce ja esta logado e no Home page', 'success')
        return redirect(url_for('home'))
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user != None:    
            senha_usuario = bcrypt.check_password_hash(user.password, form.password.data) # returns True        
        if user != None and senha_usuario == True:
            login_user(user)            
            flash(f'User {user.username.title()} connected online', 'success')
            return redirect(url_for('postagem'))
        else:
            flash('email e senha invalido', 'danger')
            return redirect(url_for('login'))            
    return render_template('login.html', form=form, legend='login', dolar=dolar[:-1])
    


@app.route('/postagem', methods=['GET', 'POST'])
@login_required
def postagem():
    form = PostForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            with app.app_context():
                post = Post(title=form.title.data, content=form.content.data, id_user=current_user.id, date_create=datetime.now())
                db.session.add(post)
                db.session.commit()
                return redirect(url_for('home'))    
    return render_template('postagem.html', legend='posts', form=form, dolar=dolar[:-1])

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post, dolar=dolar[:-1])


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', form=form, image_file=image_file, dolar=dolar[:-1])

# rota de deletar postagem
@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post', dolar=dolar[:-1])


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_create.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user, dolar=dolar[:-1])


def enviar_email(user):
    token = user.get_reset_token()
    mensagem = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email])
    mensagem.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(mensagem)    
    
    
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        enviar_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form, dolar=dolar[:-1])
    


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

# Handler para erro 404 (Not Found)
@app.errorhandler(404)
def not_found_error(error):
    return render_template('erros/404.html'), 404

# Handler para erro 500 (Internal Server Error)
@app.errorhandler(500)
def internal_error(error):
    return render_template('erros/500.html'), 500

# Handler para erro 403 (Forbidden)
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('erros/403.html'), 403