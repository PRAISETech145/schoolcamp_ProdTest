/* ─── SchoolCamp Timetable JS ─── */

document.addEventListener('DOMContentLoaded', function () {

  // ─── Auto-dismiss alerts ───
  document.querySelectorAll('.tt-alert').forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'opacity 0.4s';
      alert.style.opacity = '0';
      setTimeout(function () { alert.remove(); }, 400);
    }, 4000);
  });

  // ─── Color select visual preview ───
  const colorSelect = document.querySelector('select[name="color"]');
  if (colorSelect) {
    function updateColorPreview() {
      const val = colorSelect.value;
      colorSelect.style.borderLeft = `6px solid ${val}`;
    }
    colorSelect.addEventListener('change', updateColorPreview);
    updateColorPreview();
  }

  // ─── Course block modal (weekly grid) ───
  const modal = document.getElementById('courseModal');
  const modalBody = document.getElementById('courseModalBody');

  document.querySelectorAll('.tt-grid-course-block[data-course-id]').forEach(function (block) {
    block.addEventListener('click', function () {
      const id = this.dataset.courseId;
      const name = this.dataset.courseName || '';
      const code = this.dataset.courseCode || '';
      const lecturer = this.dataset.courseLecturer || '';
      const room = this.dataset.courseRoom || '';
      const time = this.dataset.courseTime || '';
      const duration = this.dataset.courseDuration || '';
      const notes = this.dataset.courseNotes || '';
      const color = this.dataset.courseColor || '#4CAF50';
      const editUrl = this.dataset.editUrl || '#';
      const deleteUrl = this.dataset.deleteUrl || '#';

      if (modalBody) {
        modalBody.innerHTML = `
          <div style="border-left: 5px solid ${color}; padding-left: 12px; margin-bottom: 16px;">
            <h5 style="margin:0;font-weight:800;">${name}</h5>
            ${code ? `<span style="font-size:0.8rem;color:#6b7c73;">${code}</span>` : ''}
          </div>
          <div class="course-detail-row">
            <span>🕐</span><span>${time} &nbsp;(${duration} min)</span>
          </div>
          ${lecturer ? `<div class="course-detail-row"><span>👨‍🏫</span><span>${lecturer}</span></div>` : ''}
          ${room ? `<div class="course-detail-row"><span>📍</span><span>${room}</span></div>` : ''}
          ${notes ? `<div style="margin-top:12px;font-size:0.83rem;color:#6b7c73;">${notes}</div>` : ''}
          <div style="display:flex;gap:8px;margin-top:20px;">
            <a href="${editUrl}" class="btn-sc-outline" style="flex:1;justify-content:center;font-size:0.82rem;padding:8px;">✏️ Edit</a>
            <a href="${deleteUrl}" class="btn-sc-danger" style="flex:1;justify-content:center;font-size:0.82rem;padding:8px;" onclick="return confirm('Delete this course?')">🗑️ Delete</a>
          </div>
        `;
      }

      if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
      }
    });
  });

  // Close modal
  const modalClose = document.getElementById('modalClose');
  const modalOverlay = document.getElementById('courseModal');
  if (modalClose) {
    modalClose.addEventListener('click', closeModal);
  }
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === this) closeModal();
    });
  }

  function closeModal() {
    if (modal) {
      modal.style.display = 'none';
      modal.classList.remove('show');
    }
  }

  // ─── Share link copy ───
  const copyBtn = document.getElementById('copyShareLink');
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      const link = document.getElementById('shareLinkText');
      if (link) {
        navigator.clipboard.writeText(link.textContent.trim()).then(function () {
          copyBtn.textContent = '✅ Copied!';
          setTimeout(function () { copyBtn.textContent = '📋 Copy Link'; }, 2000);
        });
      }
    });
  }

  // ─── Day tab switcher (dashboard today view) ───
  document.querySelectorAll('[data-day-tab]').forEach(function (tab) {
    tab.addEventListener('click', function () {
      const target = this.dataset.dayTab;
      document.querySelectorAll('[data-day-tab]').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('[data-day-content]').forEach(c => c.classList.add('d-none'));
      this.classList.add('active');
      const content = document.querySelector(`[data-day-content="${target}"]`);
      if (content) content.classList.remove('d-none');
    });
  });

  // ─── Swipe support for day view ───
  let touchStartX = 0;
  let touchEndX = 0;

  document.addEventListener('touchstart', function (e) {
    touchStartX = e.touches[0].clientX;
  }, { passive: true });

  document.addEventListener('touchend', function (e) {
    touchEndX = e.changedTouches[0].clientX;
    handleSwipe();
  }, { passive: true });

  function handleSwipe() {
    const diff = touchStartX - touchEndX;
    const prevLink = document.getElementById('dayNavPrev');
    const nextLink = document.getElementById('dayNavNext');

    if (Math.abs(diff) > 50) {
      if (diff > 0 && nextLink) {
        nextLink.click(); // swipe left = next day
      } else if (diff < 0 && prevLink) {
        prevLink.click(); // swipe right = prev day
      }
    }
  }

  // ─── Time field validation ───
  const startTime = document.querySelector('input[name="start_time"]');
  const endTime = document.querySelector('input[name="end_time"]');

  if (startTime && endTime) {
    endTime.addEventListener('change', function () {
      if (startTime.value && this.value && this.value <= startTime.value) {
        this.setCustomValidity('End time must be after start time');
        this.reportValidity();
      } else {
        this.setCustomValidity('');
      }
    });
  }

});
