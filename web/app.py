from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from admin.net_tcp import send
from shared import protocol

app = Flask(__name__)
app.secret_key = 'vtkd1234567890'  
    
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Helper: build payload cho request admin
def _admin_payload(extra=None):
    extra = extra or {}
    token = session.get('token')
    if token:
        base = {"token": token}
    else:
        base = {"admin_id": session.get('user_id')}
    base.update(extra)
    return base

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        res = send({
            "action": protocol.ACTIONS["login"],
            "data": {
                "username": data.get('username'),
                "password": data.get('password')
            }
        })
        
        if not res.get("ok"):
            return jsonify({"success": False, "error": res.get("error", "Đăng nhập thất bại")})
        
        user_data = res.get("data", {}) or {}
        role = user_data.get("role")
        user_id = user_data.get("user_id")
        
        if role != "admin" or not user_id:
            return jsonify({"success": False, "error": "Tài khoản này không phải admin"})
        
        session['user_id'] = user_id
        session['token'] = user_data.get('token')
        session['username'] = data.get('username')
        
        return jsonify({"success": True})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session.get('username'))

# API endpoints
@app.route('/api/users')
@login_required
def get_users():
    res = send({
        "action": protocol.ACTIONS["admin_list_users"],
        "data": _admin_payload()
    })
    if not res.get("ok"):
        return jsonify({"success": False, "error": res.get("error")})
    return jsonify({"success": True, "users": res["data"].get("users", [])})

@app.route('/api/pending-files')
@login_required
def get_pending_files():
    res = send({
        "action": protocol.ACTIONS["admin_list_pending_files"],
        "data": _admin_payload()
    })
    if not res.get("ok"):
        return jsonify({"success": False, "error": res.get("error")})
    return jsonify({"success": True, "files": res["data"].get("files", [])})

@app.route('/api/revenue')
@login_required
def get_revenue():
    action_name = "admin_revenue_stats"
    
    if action_name not in protocol.ACTIONS:
        return jsonify({"success": False, "error": "Action admin_revenue_stats không tồn tại trong protocol"})
    
    action_value = protocol.ACTIONS[action_name]
    
    payload = {
        "action": action_value,
        "data": _admin_payload()
    }
    
    print("=== Gửi request revenue ===")
    print("Payload:", payload)
    
    res = send(payload)
    
    print("=== Response từ server revenue ===")
    print(res)  # <<< In toàn bộ response
    print("===============================")
    
    if not res.get("ok"):
        error_msg = res.get("error", "Lỗi không xác định từ server")
        return jsonify({"success": False, "error": error_msg})
    
    # Thành công → trả data (có thể rỗng)
    return jsonify({
        "success": True,
        "data": res.get("data", {})
    })

@app.route('/api/file/approve', methods=['POST'])
@login_required
def approve_file():
    data = request.get_json()
    file_id = data.get('file_id')
    
    res = send({
        "action": protocol.ACTIONS["admin_approve_file"],
        "data": _admin_payload({"file_id": file_id})
    })
    
    return jsonify({
        "success": res.get("ok", False),
        "message": res.get("message") or res.get("error")
    })

@app.route('/api/file/reject', methods=['POST'])
@login_required
def reject_file():
    data = request.get_json()
    file_id = data.get('file_id')
    
    res = send({
        "action": protocol.ACTIONS["admin_reject_file"],
        "data": _admin_payload({"file_id": file_id})
    })
    
    return jsonify({
        "success": res.get("ok", False),
        "message": res.get("message") or res.get("error")
    })

@app.route('/api/user-activity/<int:user_id>')
@login_required
def get_user_activity(user_id):
    res = send({
        "action": protocol.ACTIONS["admin_user_activity"],
        "data": _admin_payload({"user_id": user_id})
    })
    
    if not res.get("ok"):
        return jsonify({"success": False, "error": res.get("error")})
    
    return jsonify({
        "success": True,
        "items": res["data"].get("items", [])
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)