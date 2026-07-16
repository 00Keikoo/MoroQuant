export function toast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  const bgColors = {
    success: '#10B981',
    error: '#DC2626',
    info: '#3B82F6',
  };

  const container = document.createElement('div');
  container.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${bgColors[type]};
    color: white;
    padding: 12px 20px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    z-index: 9999;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    animation: slideIn 0.3s ease-out;
  `;
  container.textContent = message;

  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  `;
  document.head.appendChild(style);
  document.body.appendChild(container);

  setTimeout(() => {
    container.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => {
      document.body.removeChild(container);
      document.head.removeChild(style);
    }, 300);
  }, 3000);
}
