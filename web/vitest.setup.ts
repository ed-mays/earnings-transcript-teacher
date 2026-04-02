import "@testing-library/jest-dom";

// api.ts and chat.ts throw at module import time if NEXT_PUBLIC_API_URL is not set
process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
process.env.NEXT_PUBLIC_SUPABASE_URL = "http://localhost:54321";
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";

// jsdom does not implement scrollIntoView — stub it to avoid test errors
window.HTMLElement.prototype.scrollIntoView = function () {};
