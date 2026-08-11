# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

1. Clone the repository.
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/macOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables: The `.env` file is present in the repository. Adjust its values as needed for your development environment (see `.env` and `deploy.md` for reference).
6. Apply migrations: `python manage.py migrate`
7. Create a superuser (optional): `python manage.py createsuperuser`
8. Start the development server: `python manage.py runserver`

## Common Commands

- Start development server: `python manage.py runserver`
- Run tests: `python manage.py test` (or `python manage.py test app_label` for specific app)
- Create migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Create a superuser: `python manage.py createsuperuser`
- Collect static files (for production): `python manage.py collectstatic`
- Check for migrations: `python manage.py showmigrations`
- Run the project with ASGI (for Daphne, e.g., with WebSockets): `daphne schoolcamp.asgi:application` (or use `python manage.py runserver` which uses the Django development server; note that the project is configured for ASGI with Daphne in `asgi.py`)

## Project Structure

This is a Django project with the following main apps:

- `accounts`: Custom user model, authentication, profiles.
- `forum`: Discussion forums, threads, posts.
- `friends`: Friendship system, friend requests, etc.
- `quiz`: Quiz functionality, questions, attempts.
- `materials`: Learning materials, resources, documents.
- `GROUPS`: Group management (note: uppercase directory name).
- `chat`: Real-time chat functionality (uses Django Channels).
- `payment`: Payment processing (integrations with MTN Mobile Money, Orange Money).
- `GCE`: General Certificate Education (likely academic content).
- `timetable`: Scheduling and timetable management.
- `notifications`: User notifications system.
- `dashboard`: User dashboard, activity tracking, streaks, leaderboards, and stats (NeetCode/GitHub-style).

- `legal`: Legal pages (terms, privacy, etc.).

Key files:
- `schoolcamp/settings.py`: Main Django configuration.
- `schoolcamp/urls.py`: Root URL routing.
- `schoolcamp/asgi.py`: ASGI application entry point (for WebSockets via Daphne).
- `schoolcamp/wsgi.py`: WSGI application entry point (for traditional deployment).
- `manage.py`: Django command-line utility.
- `requirements.txt`: Python dependencies.
- `.env`: Environment variables (not committed in some workflows; but present in repo).
- `deploy.md`: Deployment instructions for Railway.

## Architecture Overview

The project uses Django as the primary web framework, with Django Channels for real-time features (chat). It uses SQLite for development (as seen in settings) but can be configured for other databases via environment variables.

Authentication is handled by a custom user model in `accounts.models.User`, using email as the username (see `ACCOUNT_AUTHENTICATION_METHOD = "email"`).

Static files are served via Whitenoise in production, with WhiteNoise storage for compression and caching.

Media files are intended to be stored on Cloudinary (as commented in settings), but currently default to local storage.

Environment variables are loaded via `python-decouple` and `python-dotenv` (see manage.py and settings).

## Dashboard App

The `dashboard` app provides a comprehensive user dashboard with activity tracking, streak tracking (NeetCode/GitHub-style), statistics, leaderboards, and API endpoints.

### Models

- **UserActivity**: Generic activity log tracking all user actions across the platform (materials, forum, groups, timetable, quiz, login). Uses GenericForeignKey for flexible content linking.
- **UserStreak**: Tracks daily login/activity streaks with freeze protection, milestones (7, 14, 30, 60, 100, 200, 365, 500, 1000 days), and progress indicators.
- **UserStats**: Aggregated statistics for leaderboards and profiles (XP, activity counts, weekly/monthly stats, global/weekly ranks).
- **WeeklyLeaderboard**: Weekly competitive leaderboard with XP-based ranking.

### Views (Function-Based Views)

- **dashboard_home**: Main dashboard with streak card, XP card, weekly rank, activity heatmap, XP breakdown, recent activity feed.
- **activity_feed**: Full paginated activity feed with filtering by type and date.
- **streak_calendar**: Year-long GitHub/NeetCode-style calendar heatmap with month-by-month view.
- **stats_detail**: Detailed statistics with charts (monthly activity, XP progression, activity type breakdown, top days).
- **leaderboard**: Weekly and all-time leaderboards (XP-based, streak-based).
- **user_profile_dashboard**: Public view of another user's dashboard (limited info).

### API Endpoints (JsonResponse for AJAX)

- **api_streak_status**: Streak data for navbar badge.
- **api_weekly_progress**: Weekly progress widget data (daily XP/activity, rank).
- **api_recent_activities**: Recent activities widget (configurable limit).

### Signals (Auto-Tracking)

Auto-tracks activities from other apps when models are saved:
- **materials**: Upload (20 XP), download (5 XP)
- **forum**: Question post (3 XP), reply (5 XP), like (1 XP)
- **GROUPS**: Create group (10 XP), join (5 XP), post (3 XP)
- **timetable**: Create timetable (5 XP), add course (2 XP)
- **quiz**: Attempt (10 XP), pass (20 XP)

Central `log_activity()` function handles activity logging, streak updates, stats recalculation, and weekly leaderboard updates.

### Templates

- `home.html`: Main dashboard with streak/XP/rank cards, weekly heatmap, activity breakdown table, recent activity feed.
- `activity_feed.html`: Filterable paginated activity list.
- `streak_calendar.html`: Year-long calendar heatmap with month navigation.
- `stats_detail.html`: Detailed stats with Chart.js visualizations.
- `leaderboard.html`: Weekly and all-time leaderboards.
- `user_profile.html`: Public profile dashboard.

### Template Tags (`dashboard_extras`)

Chart data serialization filters for Chart.js:
- `get_xp_labels`, `get_xp_data`: Monthly XP chart data
- `get_labels`, `get_counts`: Activity type doughnut chart data
- `get_months`, `get_cumulative`: XP progression line chart data
- `get_sum_attrs`: Utility to sum attributes

### Login Integration

`accounts/views.py` imports `log_login_activity` from `dashboard.signals` to track logins for streak updates.

### Architecture Notes

- Uses FBVs (Function-Based Views), no DRF
- Bootstrap 5 for styling, Chart.js for charts
- JsonResponse for AJAX endpoints
- GenericForeignKey for flexible activity linking
- XP-based gamification with weekly/monthly/all-time tracking
- Streak freeze mechanic for streak protection

## Important Notes

- The project uses environment variables for sensitive data and configuration. Refer to `.env` and `deploy.md` for required variables.
- The `SECRET_KEY` and `DEBUG` settings are read from environment variables (see settings.py lines 7-8).
- Payment integrations (MTN Mobile Money, Orange Money) are configured via environment variables.
- Email backend is configured to use SMTP (default: Gmail). Adjust `EMAIL_HOST`, `EMAIL_PORT`, etc., in `.env`.
- The project uses Django Allauth for authentication (including social authentication with Google and Facebook).
- For real-time features (chat), ensure Redis is available for production channel layers; otherwise, the in-memory channel layer is used (suitable only for development).
- When deploying, remember to set `DEBUG=False` and configure allowed hosts, CSRF trusted origins, and HTTPS settings (see commented security settings in settings.py).
- **Dashboard App**: Auto-tracks user activities across materials, forum, groups, timetable, and quiz apps via signals in `dashboard.signals`. Login activity is tracked in `accounts/views.py` via `dashboard.signals.log_login_activity`. The dashboard auto-registers activities via signals when related models are saved.

## Development Tips

- To run a specific test app: `python manage.py test accounts`
- To create a new app: `python manage.py startapp appname` (then add to `INSTALLED_APPS` and run migrations).
- To modify models, run `makemigrations` and `migrate` after changes.
- The project uses Django Crispy Forms with Bootstrap 5 for styling.
- Templates are stored in each app's `templates` directory and a global `templates` directory at the project root.
- Static files are stored in each app's `static` directory and the global `static` directory.
- Media files are stored in `media` directory (or Cloudinary if configured).

## Additional Resources

- Refer to `deploy.md` for deployment instructions on Railway.
- The `.env` file provides a template for environment variables; copy and adjust for your environment.