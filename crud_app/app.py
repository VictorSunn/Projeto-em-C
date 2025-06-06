from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secreto'

# Função para conectar ao banco de dados
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criar tabelas
def create_tables():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            idade INTEGER NOT NULL,
            cpf NOT NULL,
            doencas VARCHAR(1000),
            data_nascimento TEXT NOT NULL,
            contato_emergencia TEXT NOT NULL,
            observacoes TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY,
            item_id INTEGER,
            description TEXT NOT NULL,
            priority INTEGER NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(id)
        );
    """)
    db.commit()

create_tables()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            flash('Usuário criado! Faça login.')
            return redirect('/login')
        except:
            flash('Nome de usuário já existe!')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('menu'))
        else:
            flash('Usuário ou senha inválidos', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    username = user['username'] if user else 'Usuário'
    return render_template('menu.html', username=username)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/menu')

    db = get_db()
    items = db.execute("SELECT * FROM items WHERE user_id = ?", (session['user_id'],)).fetchall()
    user = db.execute("SELECT username FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    username = user['username'] if user else 'Usuário'
    return render_template('dashboard.html', items=items, username=username)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        idade = request.form['idade']
        cpf = request.form['cpf']
        doencas = request.form['doencas']
        data_nascimento = request.form['data_nascimento']
        contato_emergencia = request.form['contato_emergencia']
        observacoes = request.form.get('observacoes', '')

        db = get_db()
        db.execute("""
            INSERT INTO items (title, idade, cpf, doencas, data_nascimento, contato_emergencia, observacoes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, idade, cpf, doencas, data_nascimento, contato_emergencia, observacoes, session['user_id']))
        db.commit()
        return redirect('/dashboard')

    return render_template('add.html')

@app.route('/view_full/<int:item_id>')
def view_full(item_id):
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()

    if not item:
        flash("Paciente não encontrado.")
        return redirect('/dashboard')

    return render_template('view_full.html', item=item)

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        db.execute("UPDATE items SET title = ? WHERE id = ?", (title, item_id))
        db.commit()
        return redirect('/dashboard')

    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:item_id>')
def delete(item_id):
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    return redirect('/dashboard')

@app.route('/add_routine/<int:item_id>', methods=['GET', 'POST'])
def add_routine(item_id):
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    if request.method == 'POST':
        description = request.form['description']
        priority = int(request.form['priority'])
        time = request.form['time']

        db.execute("""
            INSERT INTO routines (item_id, description, priority, time)
            VALUES (?, ?, ?, ?)
        """, (item_id, description, priority, time))
        db.commit()
        return redirect(url_for('view_item', item_id=item_id))

    return render_template('add_routine.html', item_id=item_id)

@app.route('/view_item/<int:item_id>', methods=['GET'])
def view_item(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    routines = db.execute("""
        SELECT * FROM routines WHERE item_id = ? ORDER BY priority ASC, time ASC
    """, (item_id,)).fetchall()

    return render_template('view_item.html', item=item, routines=routines)

@app.route('/edit_routine/<int:routine_id>', methods=['GET', 'POST'])
def edit_routine(routine_id):
    db = get_db()
    if request.method == 'POST':
        description = request.form['description']
        priority = int(request.form['priority'])
        time = request.form['time']

        db.execute("""
            UPDATE routines
            SET description = ?, priority = ?, time = ?
            WHERE id = ?
        """, (description, priority, time, routine_id))
        db.commit()
        item_id = db.execute("SELECT item_id FROM routines WHERE id = ?", (routine_id,)).fetchone()['item_id']
        return redirect(url_for('view_item', item_id=item_id))

    routine = db.execute("SELECT * FROM routines WHERE id = ?", (routine_id,)).fetchone()
    return render_template('edit_routine.html', routine=routine)

@app.route('/delete_routine/<int:routine_id>')
def delete_routine(routine_id):
    db = get_db()
    item_id = db.execute("SELECT item_id FROM routines WHERE id = ?", (routine_id,)).fetchone()['item_id']
    db.execute("DELETE FROM routines WHERE id = ?", (routine_id,))
    db.commit()
    return redirect(url_for('view_item', item_id=item_id))

@app.route('/editar/<int:item_id>', methods=['GET', 'POST'])
def editar(item_id):
    db = get_db()
    if request.method == 'POST':
        nome = request.form['nome']
        idade = request.form['idade']
        cpf = request.form['cpf']
        doencas = request.form.get('doencas', '')
        contato_emergencia = request.form['contato_emergencia']
        observacoes = request.form.get('observacoes', '')

        db.execute("""
            UPDATE items
            SET title = ?, idade = ?, cpf = ?, doencas = ?, contato_emergencia = ?, observacoes = ?
            WHERE id = ?
        """, (nome, idade, cpf, doencas, contato_emergencia, observacoes, item_id))
        db.commit()
        return redirect(url_for('view_full', item_id=item_id))

    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return render_template('editar.html', item=item)

if __name__ == '__main__':
    app.run(debug=True)
