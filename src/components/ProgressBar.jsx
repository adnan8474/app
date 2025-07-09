import React from 'react';

export default function ProgressBar({ current, total }) {
  const percentage = Math.round((current / total) * 100);
  return (
    <div className="w-full bg-gray-700 rounded-full h-4">
      <div
        className="bg-blue-500 h-4 rounded-full transition-all"
        style={{ width: `${percentage}%` }}
      />
      <div className="text-sm text-center mt-1">
        Step {current} of {total}
      </div>
    </div>
  );
}
