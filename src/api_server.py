"""
邮件助手API服务器
提供REST API接口
"""
import os
import threading
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

from src.email_assistant import EmailAssistant

app = Flask(__name__)
CORS(app)

# 全局邮件助手实例
email_assistant = EmailAssistant()

# 全局任务线程
current_task_thread: Optional[threading.Thread] = None

@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route("/api/authenticate", methods=["POST"])
def authenticate_sender():
    """认证发件人邮箱"""
    try:
        data = request.get_json()
        sender_email = data.get("sender_email")

        if not sender_email:
            return jsonify({"success": False, "error": "缺少发件人邮箱参数"}), 400

        success = email_assistant.authenticate_sender(sender_email)
        return jsonify({"success": success})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/validate_excel", methods=["POST"])
def validate_excel():
    """验证Excel文件"""
    try:
        data = request.get_json()
        excel_file_path = data.get("excel_file_path")

        if not excel_file_path:
            return jsonify({"success": False, "error": "缺少Excel文件路径参数"}), 400

        success = email_assistant.validate_excel_file(excel_file_path)
        return jsonify({"success": success})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/preview", methods=["POST"])
def preview_emails():
    """预览待发送邮箱列表"""
    try:
        data = request.get_json()
        excel_file_path = data.get("excel_file_path")

        if not excel_file_path:
            return jsonify({"success": False, "error": "缺少Excel文件路径参数"}), 400

        result = email_assistant.preview_email_list(excel_file_path)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/send_emails", methods=["POST"])
def send_emails():
    """发送邮件"""
    global current_task_thread

    try:
        data = request.get_json()

        # 必需参数
        sender_email = data.get("sender_email")
        excel_file_path = data.get("excel_file_path")

        if not sender_email or not excel_file_path:
            return jsonify({
                "success": False,
                "error": "缺少必需参数: sender_email, excel_file_path"
            }), 400

        # 可选参数
        subject = data.get("subject")
        content = data.get("content")
        html_content = data.get("html_content")
        attachments = data.get("attachments", [])  # 附件文件ID列表
        start_time_str = data.get("start_time")
        min_interval = data.get("min_interval", 20)
        max_interval = data.get("max_interval", 90)

        # 解析开始时间
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except ValueError:
                return jsonify({
                    "success": False,
                    "error": "开始时间格式错误，请使用ISO格式"
                }), 400
        else:
            # 未指定开始时间时使用当前时间
            start_time = datetime.now()

        # 检查是否有任务正在运行
        if current_task_thread and current_task_thread.is_alive():
            return jsonify({
                "success": False,
                "error": "已有邮件发送任务正在运行"
            }), 409

        # 在后台线程中运行邮件发送
        def run_email_task():
            result = email_assistant.send_emails(
                sender_email=sender_email,
                excel_file_path=excel_file_path,
                subject=subject,
                content=content,
                html_content=html_content,
                attachments=attachments,
                start_time=start_time,
                min_interval=min_interval,
                max_interval=max_interval
            )
            return result

        current_task_thread = threading.Thread(target=run_email_task, daemon=True)
        current_task_thread.start()

        return jsonify({
            "success": True,
            "message": "邮件发送任务已启动",
            "task_id": id(current_task_thread)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/status", methods=["GET"])
def get_status():
    """获取调度器状态"""
    try:
        status = email_assistant.get_scheduler_status()
        return jsonify({"success": True, "status": status})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/pause", methods=["POST"])
def pause_sending():
    """暂停发送"""
    try:
        email_assistant.pause_sending()
        return jsonify({"success": True, "message": "邮件发送已暂停"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/resume", methods=["POST"])
def resume_sending():
    """恢复发送"""
    try:
        email_assistant.resume_sending()
        return jsonify({"success": True, "message": "邮件发送已恢复"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def stop_sending():
    """停止发送"""
    try:
        email_assistant.stop_sending()
        return jsonify({"success": True, "message": "邮件发送已停止"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/statistics", methods=["POST"])
def get_statistics():
    """获取统计信息"""
    try:
        data = request.get_json()
        excel_file_path = data.get("excel_file_path")

        if not excel_file_path:
            return jsonify({"success": False, "error": "缺少Excel文件路径参数"}), 400

        result = email_assistant.get_statistics(excel_file_path)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/validate_templates", methods=["POST"])
def validate_templates():
    """验证模板兼容性"""
    try:
        data = request.get_json()
        excel_file_path = data.get("excel_file_path")

        if not excel_file_path:
            return jsonify({"success": False, "error": "缺少Excel文件路径参数"}), 400

        result = email_assistant.validate_templates(excel_file_path)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/preview_template_emails", methods=["POST"])
def preview_template_emails():
    """预览基于模板的邮件内容"""
    try:
        data = request.get_json()
        excel_file_path = data.get("excel_file_path")
        max_previews = data.get("max_previews", 3)

        if not excel_file_path:
            return jsonify({"success": False, "error": "缺少Excel文件路径参数"}), 400

        result = email_assistant.preview_template_emails(excel_file_path, max_previews)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/send_template_emails", methods=["POST"])
def send_template_emails():
    """基于模板发送邮件"""
    global current_task_thread

    try:
        data = request.get_json()
        sender_email = data.get("sender_email")
        excel_file_path = data.get("excel_file_path")
        start_time_str = data.get("start_time")
        min_interval = data.get("min_interval", 20)
        max_interval = data.get("max_interval", 90)

        if not sender_email or not excel_file_path:
            return jsonify({"success": False, "error": "缺少必需参数"}), 400

        # 解析开始时间
        start_time = None
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except ValueError:
                return jsonify({"success": False, "error": "开始时间格式错误"}), 400
        else:
            # 未指定开始时间时使用当前时间
            start_time = datetime.now()

        def run_task():
            return email_assistant.send_template_emails(
                sender_email=sender_email,
                excel_file_path=excel_file_path,
                start_time=start_time,
                min_interval=min_interval,
                max_interval=max_interval
            )

        # 启动后台任务
        current_task_thread = threading.Thread(target=run_task, daemon=True)
        current_task_thread.start()

        return jsonify({
            "success": True,
            "message": "基于模板的邮件发送任务已启动",
            "task_id": f"template_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({"success": False, "error": "API端点不存在"}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({"success": False, "error": "服务器内部错误"}), 500

def create_app():
    """创建Flask应用"""
    return app

def run_server(host="127.0.0.1", port=5000, debug=False):
    """运行API服务器"""
    print(f"启动邮件助手API服务器...")
    print(f"地址: http://{host}:{port}")
    print(f"API文档:")
    print(f"  健康检查: GET /api/health")
    print(f"  认证邮箱: POST /api/authenticate")
    print(f"  验证Excel: POST /api/validate_excel")
    print(f"  预览邮箱: POST /api/preview")
    print(f"  发送邮件: POST /api/send_emails")
    print(f"  获取状态: GET /api/status")
    print(f"  暂停发送: POST /api/pause")
    print(f"  恢复发送: POST /api/resume")
    print(f"  停止发送: POST /api/stop")
    print(f"  获取统计: POST /api/statistics")
    print(f"  验证模板: POST /api/validate_templates")
    print(f"  预览模板邮件: POST /api/preview_template_emails")
    print(f"  发送模板邮件: POST /api/send_template_emails")

    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="邮件助手API服务器")
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    parser.add_argument("--port", type=int, default=5000, help="服务器端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()
    run_server(args.host, args.port, args.debug)