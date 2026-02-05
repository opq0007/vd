"""
Gradio 界面鉴权组件

提供用户登录、会话管理等 UI 组件。
"""

import gradio as gr
from api.auth import AuthService
from utils.logger import Logger
from config import config


def create_login_interface():
    """
    创建登录界面
    
    Returns:
        gr.Blocks: 登录界面组件
    """
    login_css = """
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .login-box {
        background: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        max-width: 400px;
        width: 100%;
    }
    .login-title {
        text-align: center;
        margin-bottom: 30px;
        color: #333;
        font-size: 24px;
        font-weight: bold;
    }
    .login-info {
        margin-top: 20px;
        text-align: center;
        color: #666;
        font-size: 12px;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 8px;
    }
    """

    with gr.Blocks(css=login_css, title="登录 - 整合版 Whisper 服务") as login_demo:
        gr.HTML("""
        <div class="login-container">
            <div class="login-box">
                <div class="login-title">🔐 用户登录</div>
            </div>
        </div>
        """)
        
        with gr.Row():
            with gr.Column():
                username_input = gr.Textbox(
                    label="用户名",
                    placeholder="请输入用户名",
                    type="text",
                    autofocus=True
                )
                password_input = gr.Textbox(
                    label="密码",
                    placeholder="请输入密码",
                    type="password"
                )
                
                with gr.Row():
                    login_btn = gr.Button("登录", variant="primary", size="lg", scale=3)
                    clear_btn = gr.Button("清空", variant="secondary", size="lg", scale=1)
                
                login_message = gr.Textbox(
                    label="",
                    visible=False,
                    interactive=False,
                    elem_classes="login-message"
                )
                
                session_id_state = gr.State(value="")
                login_success_state = gr.State(value=False)

                # 登录按钮点击事件
                def handle_login(username: str, password: str) -> tuple:
                    """处理登录请求"""
                    success, message, session_id = login_user(username, password)
                    
                    # 根据登录结果显示不同的消息样式
                    if success:
                        msg_display = f"✅ {message}"
                    else:
                        msg_display = f"❌ {message}"
                    
                    return (
                        msg_display,  # 登录消息
                        gr.update(visible=True),  # 显示消息
                        session_id,  # 会话ID
                        success  # 登录状态
                    )

                login_btn.click(
                    fn=handle_login,
                    inputs=[username_input, password_input],
                    outputs=[login_message, login_message, session_id_state, login_success_state]
                )
                
                # 清空按钮点击事件
                clear_btn.click(
                    fn=lambda: ("", "", gr.update(visible=False), "", False),
                    outputs=[username_input, password_input, login_message, login_message, login_success_state]
                )
        
        gr.HTML("""
        <div class="login-info">
            <p><strong>登录说明：</strong></p>
            <p>用户名：<code>admin</code></p>
            <p>密码：<code>API_TOKEN</code> 配置值</p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                💡 提示：界面登录密码与 API Token 统一，使用相同的配置值
            </p>
        </div>
        """)
        
        # 添加登录成功后的提示
        login_success_state.change(
            fn=lambda success: gr.update(visible=True, value="🎉 登录成功！正在跳转...") if success else gr.update(),
            inputs=[login_success_state],
            outputs=[login_message]
        )

    return login_demo


def login_user(username: str, password: str) -> tuple:
    """
    用户登录函数
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        tuple: (success: bool, message: str, session_id: str)
    """
    if not username or not password:
        return False, "用户名和密码不能为空！", ""
    
    # 验证用户凭据
    if AuthService.verify_user(username, password):
        # 创建会话
        session_id = AuthService.create_gradio_session(username)
        Logger.info(f"User {username} logged in successfully")
        return True, "登录成功！", session_id
    else:
        Logger.warning(f"Failed login attempt for user: {username}")
        return False, "用户名或密码错误！", ""


def verify_session(session_id: str) -> tuple:
    """
    验证会话函数
    
    Args:
        session_id: 会话ID
        
    Returns:
        tuple: (valid: bool, username: str)
    """
    if not session_id:
        return False, ""
    
    username = AuthService.verify_gradio_session(session_id)
    if username:
        return True, username
    return False, ""


def logout_user(session_id: str) -> tuple:
    """
    用户登出函数
    
    Args:
        session_id: 会话ID
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not session_id:
        return False, "会话无效"
    
    if AuthService.revoke_gradio_session(session_id):
        Logger.info(f"User logged out successfully")
        return True, "已退出登录"
    return False, "会话无效"


def create_auth_interface():
    """
    创建完整的鉴权界面（包括登录和登出功能）
    
    Returns:
        gr.Blocks: 完整的鉴权界面组件
    """
    with gr.Blocks() as auth_demo:
        # 登录状态
        session_state = gr.State(value="")
        is_logged_in = gr.State(value=False)
        current_user = gr.State(value="")
        
        # 登录界面
        with gr.Row(visible=True) as login_section:
            with gr.Column():
                gr.Markdown("## 🔐 用户登录")
                username_input = gr.Textbox(label="用户名", placeholder="请输入用户名")
                password_input = gr.Textbox(label="密码", placeholder="请输入密码", type="password")
                
                with gr.Row():
                    login_btn = gr.Button("登录", variant="primary")
                    clear_btn = gr.Button("清空", variant="secondary")
                
                login_message = gr.Textbox(
                    label="",
                    visible=False,
                    interactive=False
                )
                
                # 登录处理
                login_btn.click(
                    fn=login_user,
                    inputs=[username_input, password_input],
                    outputs=[gr.State(visible=False), gr.State(visible=False), session_state]
                ).then(
                    fn=lambda success, msg, sid: (
                        gr.update(visible=False) if success else gr.update(visible=True),
                        gr.update(visible=True, value=msg),
                        gr.update(value=True) if success else gr.update(value=False),
                        AuthService.verify_gradio_session(sid) if success else ""
                    ),
                    inputs=[gr.State(), gr.State(), session_state],
                    outputs=[login_section, login_message, is_logged_in, current_user]
                )
                
                # 清空处理
                clear_btn.click(
                    fn=lambda: ("", ""),
                    outputs=[username_input, password_input]
                )
        
        # 登录后的界面
        with gr.Row(visible=False) as logged_in_section:
            with gr.Column():
                gr.Markdown("### 👤 已登录用户")
                user_display = gr.Textbox(label="用户名", interactive=False)
                
                with gr.Row():
                    refresh_btn = gr.Button("刷新会话", variant="secondary")
                    logout_btn = gr.Button("退出登录", variant="stop")
                
                status_message = gr.Textbox(
                    label="状态",
                    visible=False,
                    interactive=False
                )
                
                # 刷新会话
                refresh_btn.click(
                    fn=verify_session,
                    inputs=[session_state],
                    outputs=[gr.State(visible=False), user_display]
                )
                
                # 登出处理
                logout_btn.click(
                    fn=logout_user,
                    inputs=[session_state],
                    outputs=[gr.State(visible=False), gr.State(visible=False)]
                ).then(
                    fn=lambda success, msg: (
                        gr.update(visible=True) if success else gr.update(visible=False),
                        gr.update(visible=False) if success else gr.update(visible=True),
                        gr.update(visible=True, value=msg),
                        gr.update(value=""),
                        gr.update(value=False)
                    ),
                    inputs=[gr.State(), gr.State()],
                    outputs=[login_section, logged_in_section, status_message, current_user, is_logged_in]
                )
        
        # 显示用户信息
        current_user.change(
            fn=lambda user: gr.update(value=user),
            inputs=[current_user],
            outputs=[user_display]
        )
        
        # 默认账号提示
        gr.HTML("""
        <div style="margin-top: 20px; padding: 10px; background: #e3f2fd; border-radius: 5px; color: #1565c0; font-size: 12px;">
            <p><strong>登录说明：</strong></p>
            <p>用户名：<code>admin</code></p>
            <p>密码：<code>API_TOKEN</code> 配置值</p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                💡 提示：界面登录密码与 API Token 统一，使用相同的配置值
            </p>
        </div>
        """)
    
    return auth_demo