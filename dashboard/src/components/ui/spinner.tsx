export function Spinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="relative">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-gray-700 border-t-blue-500" />
        <div className="absolute inset-0 h-10 w-10 animate-spin-slow rounded-full border-2 border-transparent border-b-violet-500 opacity-40" />
      </div>
    </div>
  );
}
