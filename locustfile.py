"""
╔══════════════════════════════════════════════════════════════╗
║         SCHOOLCAMP — Locust Load Testing Script              ║
║                                                              ║
║  Install:  pip install locust                                ║
║  Run:      locust -f locustfile.py --host=http://127.0.0.1:8000
║  Web UI:   http://localhost:8089                             ║
╚══════════════════════════════════════════════════════════════╝
"""

import random
import string
from locust import HttpUser, TaskSet, task, between, events
from locust.exception import RescheduleTask


# ── Helpers ───────────────────────────────────────────────────

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def sc_login(client, username, password):
    """
    Correct Django login flow:
      1. GET /accounts/login/  → sets csrftoken cookie
      2. Read token from cookie (NOT from HTML)
      3. POST with token in BOTH form data AND X-CSRFToken header
      4. Verify login succeeded by checking response
    """
    # Step 1 — GET login page to receive csrftoken cookie
    get_resp = client.get(
        '/accounts/login/',
        name='/accounts/login/ [GET]',
    )

    # Step 2 — Read CSRF token from cookie
    csrf = client.cookies.get('csrftoken', '')
    if not csrf:
        print(f'[!] No CSRF token received for {username}')
        return False

    # Step 3 — POST with CSRF in both places Django requires
    with client.post(
        '/accounts/login/',
        name='/accounts/login/ [POST]',
        data={
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf,   # required in form body
        },
        headers={
            'X-CSRFToken': csrf,           # required in header too
            'Referer': f'{client.base_url}/accounts/login/',
        },
        allow_redirects=True,
        catch_response=True,
    ) as resp:
       
        if resp.status_code == 200 and (
            'logout' in resp.text.lower() or
            'log out' in resp.text.lower() or
            username.lower() in resp.text.lower()
        ):
            resp.success()
            return True
        else:
            resp.failure(
                f'Login failed for "{username}" '
                f'— status={resp.status_code} '
                f'— CSRF={csrf[:10]}...'
            )
            return False


def sc_logout(client):
    """POST logout with current CSRF token."""
    csrf = client.cookies.get('csrftoken', '')
    client.post(
        '/accounts/logout/',
        data={'csrfmiddlewaretoken': csrf},
        headers={
            'X-CSRFToken': csrf,
            'Referer': client.base_url,
        },
        name='/accounts/logout/ [POST]',
        allow_redirects=True,
    )


def csrf(client):
    """Get current CSRF token from cookies (after any GET request)."""
    return client.cookies.get('csrftoken', '')


# ── Test users — update to match your DB ─────────────────────
TEST_USERS = [
    {'username': 'PraiseTech', 'password': 'testpass123'},
    {'username': 'Hermine',    'password': 'testpass123'},
    {'username': 'crispo',     'password': 'testpass123'},
]

SAMPLE_QUESTIONS = [
    'How do I solve quadratic equations?',
    'What is the difference between mitosis and meiosis?',
    "Explain Newton's third law with an example",
    'How do I calculate the area of a circle?',
    'What are the causes of World War 1?',
    'How does photosynthesis work?',
    'What is the Pythagorean theorem?',
    'How do I write a good essay introduction?',
]


# ══════════════════════════════════════════════════════════════
#  TASK SETS
# ══════════════════════════════════════════════════════════════

class GuestBrowsing(TaskSet):
    """
    Unauthenticated visitor browsing SchoolCamp.
    No login needed — tests public pages only.
    """

    @task(5)
    def view_forum_home(self):
        with self.client.get('/', catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f'Forum home failed: {r.status_code}')

    @task(3)
    def search_questions(self):
        query = random.choice(['math', 'biology', 'physics', 'history', 'french'])
        self.client.get(f'/?q={query}', name='/?q=[query]')

    @task(2)
    def view_login_page(self):
        self.client.get('/accounts/login/', name='/accounts/login/ [GET]')

    @task(1)
    def view_register_page(self):
        self.client.get('/accounts/register/')

    @task(2)
    def view_question_detail(self):
        pk = random.randint(1, 20)
        with self.client.get(
            f'/forum/{pk}/', name='/forum/[id]/', catch_response=True
        ) as r:
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f'Unexpected: {r.status_code}')


class AuthenticatedFlow(TaskSet):
    """
    Full authenticated student flow.
    Logs in once at start, runs tasks, logs out at end.
    """

    def on_start(self):
        """Login once when this virtual user starts."""
        user = random.choice(TEST_USERS)
        self.current_user = user
        ok = sc_login(self.client, user['username'], user['password'])
        if not ok:
            # If login fails, stop this user entirely
            raise RescheduleTask()

    def on_stop(self):
        sc_logout(self.client)

    # ── Forum ─────────────────────────────────────────────────

    @task(8)
    def browse_forum(self):
        self.client.get('/')

    @task(4)
    def view_question(self):
        pk = random.randint(1, 20)
        with self.client.get(
            f'/forum/{pk}/', name='/forum/[id]/', catch_response=True
        ) as r:
            if r.status_code in (200, 404):
                r.success()

    @task(2)
    def search_forum(self):
        q = random.choice(['quadratic', 'mitosis', 'newton', 'histoire', 'chimie'])
        self.client.get(f'/?q={q}', name='/?q=[query]')

    @task(1)
    def like_question(self):
        pk = random.randint(1, 20)
        token = csrf(self.client)
        with self.client.post(
            f'/forum/{pk}/like/',
            name='/forum/[id]/like/',
            data={'csrfmiddlewaretoken': token},
            headers={
                'X-CSRFToken': token,
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.client.base_url}/forum/{pk}/',
            },
            catch_response=True,
        ) as r:
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f'Like failed: {r.status_code}')

    @task(1)
    def ask_question(self):
        # First GET the ask page to get fresh CSRF
        self.client.get('/forum/ask/', name='/forum/ask/ [GET]')
        token = csrf(self.client)
        title = random.choice(SAMPLE_QUESTIONS) + f' [{random_string(4)}]'
        with self.client.post(
            '/forum/ask/',
            name='/forum/ask/ [POST]',
            data={
                'title': title,
                'body': f'I need help with this topic. {random_string(30)}',
                'tags': 'test',
                'csrfmiddlewaretoken': token,
            },
            headers={
                'X-CSRFToken': token,
                'Referer': f'{self.client.base_url}/forum/ask/',
            },
            allow_redirects=True,
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f'Ask question failed: {r.status_code}')

    # ── Groups ────────────────────────────────────────────────

    @task(3)
    def browse_groups(self):
        self.client.get('/Group/')

    @task(2)
    def view_group(self):
        pk = random.randint(1, 10)
        with self.client.get(
            f'/groups/{pk}/', name='/groups/[id]/', catch_response=True
        ) as r:
            if r.status_code in (200, 404):
                r.success()

    # ── Materials ─────────────────────────────────────────────

    @task(3)
    def browse_materials(self):
        self.client.get('/materials/')

    @task(1)
    def view_material(self):
        pk = random.randint(1, 10)
        with self.client.get(
            f'/materials/{pk}/', name='/materials/[id]/', catch_response=True
        ) as r:
            if r.status_code in (200, 404):
                r.success()

    # ── Quiz ──────────────────────────────────────────────────

    @task(2)
    def browse_quizzes(self):
        self.client.get('/quiz/')

    @task(1)
    def view_quiz(self):
        pk = random.randint(1, 5)
        with self.client.get(
            f'/quiz/{pk}/', name='/quiz/[id]/', catch_response=True
        ) as r:
            if r.status_code in (200, 404):
                r.success()

    # ── Chat ──────────────────────────────────────────────────

    @task(4)
    def view_inbox(self):
        self.client.get('/chat/')

    @task(2)
    def check_unread_messages(self):
        with self.client.get(
            '/chat/api/unread/', catch_response=True
        ) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f'Unread count failed: {r.status_code}')

    # ── Friends ───────────────────────────────────────────────

    @task(2)
    def view_friends(self):
        self.client.get('/friends/')

    @task(1)
    def check_friend_requests(self):
        with self.client.get(
            '/friends/pending/count/', catch_response=True
        ) as r:
            if r.status_code in (200, 404):
                r.success()

    # ── Notifications ─────────────────────────────────────────

    @task(2)
    def view_notifications(self):
        self.client.get('/notification/')

    # ── Profile ───────────────────────────────────────────────

    @task(2)
    def view_own_profile(self):
        username = self.current_user['username']
        self.client.get(
            f'/accounts/profile/{username}/',
            name='/accounts/profile/[username]/'
        )

    # ── Subscription ──────────────────────────────────────────

    @task(1)
    def view_subscription(self):
        self.client.get('/payment/subscription/')


class PaymentFlow(TaskSet):
    """
    Tests the full MTN MoMo subscription payment flow:
      1. View payment wall
      2. Initiate MTN payment with sandbox number
      3. Poll payment pending page
      4. Check payment status via AJAX
      5. Simulate webhook callback (SUCCESSFUL)
      6. Verify subscription activated
    """

    # MTN sandbox test numbers and their expected outcomes
    MTN_SANDBOX_NUMBERS = [
        ('46733123454', 'SUCCESSFUL'),   # always succeeds
        ('46733123450', 'FAILED'),       # always fails
        ('46733123451', 'PENDING'),      # stays pending
    ]

    def on_start(self):
        user = random.choice(TEST_USERS)
        self.current_user = user
        ok = sc_login(self.client, user['username'], user['password'])
        if not ok:
            raise RescheduleTask()
        self.last_payment_pk = None
        self.last_reference = None

    def on_stop(self):
        sc_logout(self.client)

    # ── Step 1: View payment wall ──────────────────────────────

    @task(5)
    def view_payment_wall(self):
        with self.client.get(
            '/payment/',
            name='/payment/ [GET]',
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f'Payment wall failed: {r.status_code}')

    # ── Step 2: View subscription status ──────────────────────

    @task(3)
    def view_subscription_status(self):
        with self.client.get(
            '/payment/subscription/',
            name='/payment/subscription/ [GET]',
            catch_response=True,
        ) as r:
            if r.status_code in (200, 302):
                r.success()
            else:
                r.failure(f'Subscription status failed: {r.status_code}')

    # ── Step 3: Initiate MTN payment (SUCCESSFUL number) ──────

    @task(3)
    def initiate_mtn_payment_success(self):
        """Initiate payment with the sandbox SUCCESSFUL number."""
        self.client.get('/payment/', name='/payment/ [GET]')
        token = csrf(self.client)

        with self.client.post(
            '/payment/initiate/',
            name='/payment/initiate/mtn [POST]',
            data={
                'provider': 'mtn',
                'phone_number': '46733123454',   # ✅ always SUCCESSFUL
                'csrfmiddlewaretoken': token,
            },
            headers={
                'X-CSRFToken': token,
                'Referer': f'{self.client.base_url}/payment/',
            },
            allow_redirects=True,
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                # Extract payment pk from redirect URL if available
                if '/payment/pending/' in r.url:
                    try:
                        self.last_payment_pk = r.url.rstrip('/').split('/')[-1]
                    except Exception:
                        pass
                r.success()
            else:
                r.failure(f'MTN payment initiation failed: {r.status_code}')

    # ── Step 4: Initiate MTN payment (FAILED number) ──────────

    @task(1)
    def initiate_mtn_payment_failed(self):
        """Initiate payment with the sandbox FAILED number — tests error handling."""
        self.client.get('/payment/', name='/payment/ [GET]')
        token = csrf(self.client)

        with self.client.post(
            '/payment/initiate/',
            name='/payment/initiate/mtn-fail [POST]',
            data={
                'provider': 'mtn',
                'phone_number': '46733123450',   # ❌ always FAILED
                'csrfmiddlewaretoken': token,
            },
            headers={
                'X-CSRFToken': token,
                'Referer': f'{self.client.base_url}/payment/',
            },
            allow_redirects=True,
            catch_response=True,
        ) as r:
            # 200 = pending page shown, 302 = redirect — both are valid
            if r.status_code in (200, 302):
                r.success()
            else:
                r.failure(f'MTN failed-payment test returned: {r.status_code}')

    # ── Step 5: Poll pending page ──────────────────────────────

    @task(2)
    def poll_payment_pending(self):
        """Simulate user waiting on the pending page."""
        pk = self.last_payment_pk or random.randint(1, 10)
        with self.client.get(
            f'/payment/pending/{pk}/',
            name='/payment/pending/[pk]/ [GET]',
            catch_response=True,
        ) as r:
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f'Pending page failed: {r.status_code}')

    # ── Step 6: AJAX status check (frontend polling) ──────────

    @task(4)
    def ajax_check_payment_status(self):
        """Simulates the frontend JS polling payment status every few seconds."""
        pk = self.last_payment_pk or random.randint(1, 10)
        with self.client.get(
            f'/payment/status/{pk}/',
            name='/payment/status/[pk]/ [AJAX]',
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            },
            catch_response=True,
        ) as r:
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f'Status AJAX failed: {r.status_code}')

    # ── Step 7: Simulate MTN webhook callback ─────────────────

    @task(1)
    def simulate_mtn_webhook(self):
        """
        Simulates MTN MoMo sending a payment callback to our webhook.
        Uses a unique reference each time to avoid duplicate key errors.
        """
        import uuid
        ref = f"SC-TEST-{uuid.uuid4().hex[:8].upper()}"

        with self.client.post(
            '/payment/webhook/',
            name='/payment/webhook/ [MTN callback]',
            json={
                'financialTransactionId': f'TXN{random.randint(100000, 999999)}',
                'externalId': ref,
                'amount': '200',
                'currency': 'EUR',
                'payer': {
                    'partyIdType': 'MSISDN',
                    'partyId': '46733123454',
                },
                'payerMessage': 'Schoolcamp Subscription',
                'payeeNote': f'SchoolCamp ref {ref}',
                'status': 'SUCCESSFUL',
            },
            headers={
                'Content-Type': 'application/json',
            },
            catch_response=True,
        ) as r:
            # 200 = webhook processed, 404 = ref not in DB (expected in load test)
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f'Webhook failed: {r.status_code} — {r.text[:100]}')

    # ── Step 8: View success page ──────────────────────────────

    @task(1)
    def view_payment_success(self):
        with self.client.get(
            '/payment/success/',
            name='/payment/success/ [GET]',
            catch_response=True,
        ) as r:
            if r.status_code in (200, 302):
                r.success()
            else:
                r.failure(f'Success page failed: {r.status_code}')

    # ── Step 9: Dev confirm payment (sandbox only) ────────────

    @task(1)
    def dev_confirm_payment(self):
        """
        Hits the DEV-only confirm endpoint to simulate subscription activation.
        Remove this task when deploying to production.
        """
        pk = self.last_payment_pk or random.randint(1, 10)
        token = csrf(self.client)
        with self.client.post(
            f'/payment/confirm/{pk}/',
            name='/payment/confirm/[pk]/ [DEV]',
            data={'csrfmiddlewaretoken': token},
            headers={
                'X-CSRFToken': token,
                'Referer': f'{self.client.base_url}/payment/pending/{pk}/',
            },
            allow_redirects=True,
            catch_response=True,
        ) as r:
            if r.status_code in (200, 404, 302):
                r.success()
            else:
                r.failure(f'Dev confirm failed: {r.status_code}')


# ══════════════════════════════════════════════════════════════
#  USER CLASSES
# ══════════════════════════════════════════════════════════════

class GuestUser(HttpUser):
    """Unauthenticated visitor — public pages only."""
    tasks = [GuestBrowsing]
    wait_time = between(2, 5)
    weight = 3


class StudentUser(HttpUser):
    """Regular logged-in student — most common user type."""
    tasks = [AuthenticatedFlow]
    wait_time = between(3, 8)
    weight = 5


class PowerUser(HttpUser):
    """Heavy user — very active, short waits."""
    tasks = [AuthenticatedFlow]
    wait_time = between(1, 3)
    weight = 1


class PaymentUser(HttpUser):
    """User testing payment flow."""
    tasks = [PaymentFlow]
    wait_time = between(5, 15)
    weight = 1


# ══════════════════════════════════════════════════════════════
#  EVENT HOOKS
# ══════════════════════════════════════════════════════════════

@events.request.add_listener
def on_request(request_type, name, response_time, response_length,
               exception, context, **kwargs):
    if response_time > 2000:
        print(f'⚠️  SLOW: {request_type} {name} → {response_time:.0f}ms')


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("""
╔══════════════════════════════════════════════╗
║   🏕  SchoolCamp Load Test Starting...       ║
║   • GuestUser    → browse without login      ║
║   • StudentUser  → full authenticated flow   ║
║   • PowerUser    → heavy posting/chatting    ║
║   • PaymentUser  → MTN MoMo payment flow     ║
║                                              ║
║   MTN Sandbox Numbers:                       ║
║   46733123454 → SUCCESSFUL ✅                ║
║   46733123450 → FAILED     ❌                ║
║   46733123451 → PENDING    ⏳                ║
╚══════════════════════════════════════════════╝
    """)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("""
╔══════════════════════════════════════════════╗
║   🏕  SchoolCamp Load Test Complete!         ║
╚══════════════════════════════════════════════╝
    """)