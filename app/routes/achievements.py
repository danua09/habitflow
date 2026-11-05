from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.achievement import Achievement, UserAchievement

achievements_bp = Blueprint('achievements', __name__, url_prefix='/achievements')


@achievements_bp.route('/')
@login_required
def index():
    all_achievements = Achievement.query.all()
    earned_ids = {ua.achievement_id for ua in
                  UserAchievement.query.filter_by(user_id=current_user.id).all()}

    earned = []
    locked = []
    for a in all_achievements:
        if a.id in earned_ids:
            ua = UserAchievement.query.filter_by(
                user_id=current_user.id, achievement_id=a.id
            ).first()
            earned.append({'achievement': a, 'earned_at': ua.earned_at})
        else:
            locked.append(a)

    return render_template('achievements/index.html',
                           earned=earned, locked=locked,
                           total=len(all_achievements),
                           earned_count=len(earned))
