from flask import render_template,redirect,session,request, flash, jsonify
from src import app
from src.models.user import User
from src.models.proyects import Proyect
from src.models.tgs import Tgs
from src.models.circuits import Circuit
from src.models.loads import Load
from src.models.tds import Tds

from flask_bcrypt import Bcrypt
bcrypt = Bcrypt(app)


#  -----------MAIN PAGE --------------------

@app.route('/loadbox/')
def loadbox():
    if 'user_id' not in session:
        return redirect('/logout')

    data ={'id': session['user_id']}

    user = User.get_by_id(data)
    proyects = Proyect.get_all_proyect_by_user_id(data)
    tgs = Proyect.get_all_tgs_by_proyect_id_and_user_id(data)
    wires= Proyect.get_all_wires()
    circuits = Circuit.get_all_circuits_by_user_user_id(data)
    return render_template('house.html', user=user, proyects=proyects, tgs=tgs, wires=wires, circuits=circuits)

# -------------NEW PROYECT------------------

@app.route('/new_proyect', methods=['POST'])
def new_proyect():
    if 'user_id' not in session:
        return redirect('/logout')
    data = {
        'name': request.form['name'],
        'user_id': session['user_id']
    }

    Proyect.save(data)
    return redirect('/loadbox')

# ---------------ADD NEW GENERAL TABLE------------------

@app.route('/add_tgs', methods=['POST'])
def add_tgs():
    if 'user_id' not in session:
        return redirect('/logout')
    
    data = {
        'name': request.form['name'],
        'tag': request.form['tag'],
        'proyect_id': request.form['proyect_id']
    }

    Tgs.add_tgs(data)
    return redirect('/loadbox')

# ---------------ADD NEW DISTRIBUCION TABLE------------------

@app.route('/add_tds', methods=['POST'])
def add_tds():
    if 'user_id' not in session:
        return redirect('/logout')
    
    data = {
        'name': request.form['name'],
        'tag': request.form['tag'],
        'tg_id': request.form['tg_id']
    }
    print(data)
    Tds.add_tds(data)
    return redirect('/loadbox')

# -------------- CREATE CIRCUITS--------------------------

@app.route('/new_circuit', methods=['POST'])
def new_circuits():

    if 'user_id' not in session:
        return redirect('/logout')
    
    if not Proyect.validate_circuit(request.form):
        return redirect('/loadbox/')

    data = {
        'name': request.form['name'],
        'ref': request.form['ref'],
        'single_voltage': request.form['single_voltage'],
        'method': request.form['method'],
        'fp': request.form['fp'],
        'length': request.form['length'],
        'tg_id' : request.form['tg_id']
    }
    td_id = request.form.get('td_id')
    if td_id and td_id.isdigit():
        data['td_id'] = request.form['td_id']
    else:
        data['td_id'] = None

    print(data['td_id'])

    data['wires'] = request.form['type_isolation']
    data['type_circuit'] = request.form['type_circuit']
    circuit_id = Circuit.add_circuit(data)
    data['qty'] = request.form['qty']
    data['power'] = request.form['power']
    total_power = round((int(data['qty']) * float(data['power']))/1000,2)
    total_current = round(total_power/float(data['single_voltage']),2)
    data1 = {'method':data['method'],'total_current':total_current}
    current_by_method= Proyect.current(data1)
    print(current_by_method)
    vp = (2 * 0.018 * float(total_current) * float(data['length']))/float(current_by_method[0]['secction_mm2'])
    print(vp)
    data2 = {}                                                                 
    if vp < 4.5:
        pass
    else: 
        allcurrent_by_method = Circuit.vp_real(data1)
        for all in allcurrent_by_method:
            print(all)
            if float(2 * 0.018 * float(total_current) * float(data['length']))/float((all['secction_mm2'])) < 4.5:
                data1['total_current'] = all['method']
                # data2['secctionmm2'] = all['secction_mm2']
                break

    print(data1)
    print(data2)                                                              
    current_by_method2 = Proyect.updated_current(data1)
    print(current_by_method2)
    data2 = {}
    data2['circuit_id'] = circuit_id
    data2['secctionmm2'] = float(current_by_method2[0]['secction_mm2'])
    data2['current_by_method'] = current_by_method2[0][data['method']]
    data2['breakers'] = current_by_method2[0]['disyuntor']
    data2['elect_differencial'] = current_by_method2[0]['diferencial']
    print(data2)
    Circuit.update_method(data2)
    Circuit.update_secctionmm2(data2)
    Circuit.update_breakers(data2)
    Circuit.update_elect_differencial(data2)
    data3 = { 'vp':round((2*0.018*float(data['length'])*float(total_current))/data2['secctionmm2'],2), 'circuit_id':circuit_id}
    print(data3)
    Circuit.update_vp(data3)
    if circuit_id:
        data4 = {'qty': data['qty'], 'power':data['power'], 'total_power':total_power, 'total_current': total_current,'circuit_id': circuit_id}
        Load.save(data4)
    else:
        pass
    return redirect('/loadbox')

# --------- SUMMARY ---------------

@app.route('/pro')
def pro():
    if 'user_id' not in session:
        return redirect('/logout')

    data ={'id': session['user_id']}

    user = User.get_by_id(data)
    return render_template('summary.html', user=user)




# ------------ AJAX----------------------

@app.route('/api/tgs', methods=['POST'])
def get_tgs():
    proyect = request.form['proyect']
    tgs1 = Tgs.get_tgs_by_project({'proyect_id': proyect})
    print(tgs1)
    return jsonify(tgs1)

@app.route('/api/tds', methods=['POST'])
def get_tds():
    tg_id = request.form['tgs']
    circuit_tg = Circuit.get_all_circuits_by_tg_id({'tg_id':tg_id})
    tgs = Tds.get_all_tds_by_tg_id({'tg_id':tg_id})
    return jsonify(tgs, circuit_tg)


@app.route('/api/circuits_td', methods=['POST'])
def get_all_circuits_by_tds():

    tgs_values = request.form.getlist('tgs[]')
    tds_values = request.form.getlist('tds[]')

    data = {
        'tg_id': tgs_values,
        'td_id': tds_values
    }
    circuit_td = {}
    if data['td_id'] and data['tg_id']:
        circuit_td = Circuit.get_all_circuit_and_tds_by_tg(data)
    else:
        pass
    return jsonify(circuit_td)

# ----------- AJAX FROM AJAX ABOUT DETAIL CIRCUITS BY TDS AND TGS -----------------
@app.route('/api/detail/tds', methods=['POST'])
def detai_circuit_tds():
    circuit_id = request.form['tds']
    print(circuit_id)
    circuitos = Circuit.detail_circuit_by_id({'circuit_id': circuit_id})
    print(circuitos)
    return jsonify(circuitos)