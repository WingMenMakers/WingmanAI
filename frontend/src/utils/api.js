export async function apiFetch(path, options = {}) {
    return fetch(path, {
        credentials: "include",
        ...options,
    });
}
