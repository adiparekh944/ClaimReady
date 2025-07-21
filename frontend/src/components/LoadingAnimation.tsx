'use client';

export default function LoadingAnimation() {
  return (
    <div className="w-full flex flex-col items-center justify-center mt-6">
      <span className="text-sm font-medium text-blue-600 mb-4">Loading...</span>
      <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-500"></div>
    </div>
  );
}
