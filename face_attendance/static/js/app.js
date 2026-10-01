/* static/js/app.js — shared utilities */

// Auto-dismiss Bootstrap alerts after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert.alert-dismissible').forEach(el => {
    setTimeout(() => {
      const instance = bootstrap.Alert.getOrCreateInstance(el);
      if (instance) instance.close();
    }, 4000);
  });

  // Activate tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // Sidebar toggle (mobile)
  const toggleBtn = document.getElementById('sidebarToggleBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      document.querySelector('.sidebar')?.classList.toggle('open');
    });
  }
});

// Confirm delete helper
function confirmDelete(url, msg = 'Are you sure you want to delete this record?') {
  if (confirm(msg)) window.location.href = url;
}

// Format seconds to mm:ss
function fmtTime(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
}

// Show toast notification
function showToast(msg, type = 'success') {
  const colours = { success: '#00ffb3', danger: '#ff4757', info: '#00d4ff', warning: '#ffa502' };
  const toast = document.createElement('div');
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:#131929;border:1px solid rgba(255,255,255,.08);
    border-left:3px solid ${colours[type]||colours.info};
    color:#e8edf5;padding:12px 18px;border-radius:10px;
    font-family:'Space Grotesk',sans-serif;font-size:13px;
    box-shadow:0 8px 30px rgba(0,0,0,.4);
    animation:slideUp .3s ease;
  `;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// Inject slide-up keyframe once
const style = document.createElement('style');
style.textContent = '@keyframes slideUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}';
document.head.appendChild(style);
