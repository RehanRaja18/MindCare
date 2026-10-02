// ============================================================
// MindCare — QR Code Placeholder SVG
// Replace src with real QR code image when app is live
// ============================================================

import React from 'react';

const QRCode: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div
    className={`bg-white border border-gray-200 rounded-xl p-3 flex items-center justify-center ${className}`}
    role="img"
    aria-label="QR code — scan to download the MindCare app"
  >
    {/* SVG QR-like pattern (decorative placeholder) */}
    <svg width="100%" height="100%" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      {/* Corners */}
      <rect x="4" y="4" width="24" height="24" rx="3" fill="none" stroke="#111" strokeWidth="3" />
      <rect x="8" y="8" width="16" height="16" rx="1" fill="#111" />
      <rect x="52" y="4" width="24" height="24" rx="3" fill="none" stroke="#111" strokeWidth="3" />
      <rect x="56" y="8" width="16" height="16" rx="1" fill="#111" />
      <rect x="4" y="52" width="24" height="24" rx="3" fill="none" stroke="#111" strokeWidth="3" />
      <rect x="8" y="56" width="16" height="16" rx="1" fill="#111" />
      {/* Data dots */}
      {[36,40,44,36,44,36,40,44].map((x, i) => (
        <rect key={i} x={x} y={4 + i * 4} width="4" height="3" rx="0.5" fill="#111" />
      ))}
      {[4,12,20,4,12,20].map((x, i) => (
        <rect key={i} x={x} y={36 + i * 4} width="4" height="3" rx="0.5" fill="#111" />
      ))}
      {[36,44,40,36,44,40,36].map((x, i) => (
        <rect key={i} x={x} y={36 + i * 4} width="4" height="3" rx="0.5" fill="#111" />
      ))}
      {[52,60,68,52,68,60].map((x, i) => (
        <rect key={i} x={x} y={36 + i * 4} width="4" height="3" rx="0.5" fill="#111" />
      ))}
    </svg>
  </div>
);

export default QRCode;
