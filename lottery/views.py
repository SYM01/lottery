from . import app
from flask import render_template, jsonify, request, abort, redirect, url_for
from . import db


@app.route('/')
def index():
    data = db.get_lottery_list()
    return render_template('index.html', data=data)


@app.route('/save', methods=['POST'])
def save():
    _id = request.form.get('id', '').strip();
    name = request.form.get('name', '').strip();
    desc = request.form.get('desc', '').strip();
    total = int(request.form.get('total', 1));
    src = request.form.get('src', '').strip();
    batch = int(request.form.get('batch', 1));

    try:
        _id = int(_id)
    except: 
        _id = None
        
    if len(name) > 0 and total > 0 and batch > 0:
        db.save_lottery(_id, name, desc, total, src, batch)
    
    return redirect(url_for('.index'))


@app.route('/gifts/del', methods=["DELETE"])
def del_gift():
    try:
        _id = int(request.form.get('id'))
    except:
        return jsonify({'suc': False})

    name =  request.form.get('name', '').strip()
    if len(name) > 0:
        db.del_gift(_id, name)
        return jsonify({'suc': True})
    
    return jsonify({'suc': False})


@app.route('/users')
def users():
    candicates = db.get_candidate_list()
    winners = db.get_winner_list()
    return render_template('users.html', candicates=candicates, winners=winners)


@app.route('/users/save', methods=["POST"])
def new_user():
    name =  request.form.get('name', '').strip()
    if len(name) > 0:
        db.new_user(name)

    return redirect(url_for('.users'))

@app.route('/users/del', methods=["DELETE"])
def del_user():
    name =  request.form.get('name', '').strip()
    if len(name) > 0:
        db.del_user(name)
        return jsonify({'suc': True})
    
    return jsonify({'suc': False})


@app.route('/winners/del', methods=["DELETE"])
def del_winner():
    try:
        _id = int(request.form.get('id'))
    except:
        return jsonify({'suc': False})

    name =  request.form.get('name', '').strip()
    if len(name) > 0:
        db.del_winner(_id, name)
        return jsonify({'suc': True})
    
    return jsonify({'suc': False})


@app.route('/show')
def show():
    data = []
    gifts = db.get_lottery_list()
    for g in gifts:
        if g['winners_count'] == 0:
            continue

        info = db.get_lottery_info(g['id'])
        if info is not None or len(info['winners']) == 0:
            data.append(info)

    return render_template('show.html', data=data)


@app.route('/lottery/<int:_id>')
def lottery(_id:int):
    data = db.get_lottery_info(_id)
    if data is None:
        abort(404)
    
    recommends = db.get_not_full_lottery_list(4, _id)
    return render_template('lottery.html', data=data, recommends=recommends)


@app.route('/lottery/new/<int:_id>', methods=['GET'])
def lottery_check(_id:int):
    data = db.get_lottery_info(_id)
    if data is None:
        abort(404)

    return jsonify(data)

@app.route('/lottery/new/<int:_id>', methods=['POST'])
def lottery_confirm(_id:int):
    data = request.get_json()
    if data is None:
        abort(404)
    
    names = []
    for i in data:
        names.append(str(i).strip())

    data = db.new_winners(_id, names)
    return jsonify(data)