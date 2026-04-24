from app.extensions import db
from app.models import User, Role
from app.utils import (
    PERMISSION_VIEW,
    PERMISSION_CREATE_SURVEY,
    PERMISSION_EDIT_SURVEY,
    PERMISSION_DELETE_SURVEY,
    PERMISSION_VIEW_STATS,
    PERMISSION_MANAGE_USERS,
    PERMISSION_ADMIN
)


def init_roles():
    admin_permissions = (
        PERMISSION_VIEW |
        PERMISSION_CREATE_SURVEY |
        PERMISSION_EDIT_SURVEY |
        PERMISSION_DELETE_SURVEY |
        PERMISSION_VIEW_STATS |
        PERMISSION_MANAGE_USERS |
        PERMISSION_ADMIN
    )
    
    survey_creator_permissions = (
        PERMISSION_VIEW |
        PERMISSION_CREATE_SURVEY |
        PERMISSION_EDIT_SURVEY |
        PERMISSION_VIEW_STATS
    )
    
    user_permissions = PERMISSION_VIEW
    
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(
            name='admin',
            description='超级管理员 - 拥有所有权限',
            permissions=admin_permissions
        )
        db.session.add(admin_role)
    
    survey_creator_role = Role.query.filter_by(name='survey_creator').first()
    if not survey_creator_role:
        survey_creator_role = Role(
            name='survey_creator',
            description='问卷管理员 - 可以创建和编辑问卷',
            permissions=survey_creator_permissions
        )
        db.session.add(survey_creator_role)
    
    user_role = Role.query.filter_by(name='user').first()
    if not user_role:
        user_role = Role(
            name='user',
            description='普通用户 - 只有查看权限',
            permissions=user_permissions
        )
        db.session.add(user_role)
    
    db.session.commit()
    print('默认角色已初始化完成')
    return admin_role, survey_creator_role, user_role


def init_admin_user():
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            is_active=True
        )
        admin_user.set_password('admin123')
        
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            admin_user.roles.append(admin_role)
        
        db.session.add(admin_user)
        db.session.commit()
        print('默认管理员账号已创建: admin / admin123')
        print('提示: 请在首次登录后修改密码')
    else:
        print('管理员账号已存在')
    
    return admin_user


def init_all():
    from flask import Flask
    from app.__init__ import create_app
    
    app = create_app('development')
    with app.app_context():
        print('开始初始化数据...')
        init_roles()
        init_admin_user()
        print('初始化完成!')


if __name__ == '__main__':
    init_all()
