export const $ = (id) => document.getElementById(id);

export const show = (id) => $(id).classList.remove('hidden');
export const hide = (id) => $(id).classList.add('hidden');
