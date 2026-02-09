
class EmailTemplates:
    """邮件模板管理类"""
    @staticmethod
    def get_register_template(code: str) -> str:
        """生成注册验证码的 HTML 模板"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                .container {{ font-family: sans-serif; padding: 20px; line-height: 1.6; color: #333; }}
                .code {{ font-size: 28px; font-weight: bold; color: #4A90E2; letter-spacing: 5px; margin: 20px 0; text-align: center; }}
                .footer {{ font-size: 14px; color: #999; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }}
                .en {{ color: #555; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>欢迎注册 openJiuwen！</h2>
                <p class="en">Welcome to openJiuwen!</p>

                <p>
                    您好，请使用以下验证码完成注册：<br>
                    <span class="en">Please use the verification code below to complete your registration:</span>
                </p>

                <div class="code">{code}</div>

                <p>
                    验证码有效期为 10 分钟。如果这不是您的操作，请忽略此邮件。<br>
                    <span class="en">The verification code is valid for 10 minutes. If you did not request this, please ignore this email.</span>
                </p>

                <div class="footer">
                    此邮件由系统自动发出，请勿回复。<br>
                    This email was sent automatically by the system. Please do not reply.
                </div>
            </div>
        </body>
        </html>
        """

    
    @staticmethod
    def get_reset_password_template(code: str) -> str:
        """生成重置密码验证码的 HTML 模板"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                .container {{ font-family: sans-serif; padding: 20px; line-height: 1.6; color: #333; }}
                .code {{ font-size: 28px; font-weight: bold; color: #E94E77; letter-spacing: 5px; margin: 20px 0; text-align: center; }}
                .footer {{ font-size: 14px; color: #999; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }}
                .en {{ color: #555; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>重置您的 openJiuwen 密码</h2>
                <p class="en">Reset Your openJiuwen Password</p>

                <p>
                    您好，请使用以下验证码完成密码重置：<br>
                    <span class="en">Please use the verification code below to reset your password:</span>
                </p>

                <div class="code">{code}</div>

                <p>
                    验证码有效期为 10 分钟。如果这不是您的操作，请忽略此邮件。<br>
                    <span class="en">The verification code is valid for 10 minutes. If you did not request this, please ignore this email.</span>
                </p>

                <div class="footer">
                    此邮件由系统自动发出，请勿回复。<br>
                    This email was sent automatically by the system. Please do not reply.
                </div>
            </div>
        </body>
        </html>
        """
