import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
})

export function setAdminPassword(password) {
  http.defaults.headers.common['X-Admin-Password'] = password || ''
}

export function clearAdminPassword() {
  delete http.defaults.headers.common['X-Admin-Password']
}

export const configApi = {
  get:    ()       => http.get('/config'),
  update: (data)   => http.put('/config', data),
}

export const playersApi = {
  list:   ()           => http.get('/players'),
  create: (data)       => http.post('/players', data),
  update: (id, data)   => http.put(`/players/${id}`, data),
  remove: (id)         => http.delete(`/players/${id}`),
}

export const roundsApi = {
  list:         ()               => http.get('/rounds'),
  create:       (data)           => http.post('/rounds', data),
  getCurrent:   ()               => http.get('/rounds/current'),
  startCurrent: (data)           => http.post('/rounds/current', data),
  get:          (id)             => http.get(`/rounds/${id}`),
  update:       (id, data)       => http.put(`/rounds/${id}`, data),
  remove:       (id)             => http.delete(`/rounds/${id}`),
  getPlayers:   (id)             => http.get(`/rounds/${id}/players`),
  addPlayer:    (id, data)       => http.post(`/rounds/${id}/players`, data),
  updatePlayer: (id, pid, data)  => http.put(`/rounds/${id}/players/${pid}`, data),
  removePlayer: (id, pid)        => http.delete(`/rounds/${id}/players/${pid}`),
  finalize:     (id)             => http.post(`/rounds/${id}/finalize`),
  importPdf:    (formData)       => http.post('/rounds/import-pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
}

export const rankingApi = {
  get:            ()                     => http.get('/ranking'),
  setActive:      (round_ids)            => http.put('/ranking/active-rounds', { round_ids }),
  updateScore:    (pid, rid, score)      => http.put(`/ranking/${pid}/${rid}`, { score }),
}

export const financialApi = {
  get:            ()           => http.get('/financial'),
  update:         (data)       => http.put('/financial', data),
  getExpenses:    ()           => http.get('/expenses'),
  createExpense:  (data)       => http.post('/expenses', data),
  updateExpense:  (id, data)   => http.put(`/expenses/${id}`, data),
  removeExpense:  (id)         => http.delete(`/expenses/${id}`),
}

export const authApi = {
  verify: (password) => http.post('/auth/verify', { password }),
}
