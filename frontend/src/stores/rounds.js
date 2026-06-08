import { ref } from 'vue'
import { roundsApi, playersApi } from '../api'

const currentRound = ref(null)
const roundPlayers = ref([])
const allPlayers = ref([])

export function useRounds() {
  async function fetchAllPlayers() {
    const { data } = await playersApi.list()
    allPlayers.value = data
  }

  async function fetchCurrent() {
    const { data } = await roundsApi.getCurrent()
    currentRound.value = data
    if (data) {
      const { data: players } = await roundsApi.getPlayers(data.id)
      roundPlayers.value = players
    } else {
      roundPlayers.value = []
    }
  }

  async function startRound(label, date) {
    const { data } = await roundsApi.startCurrent({ label: label || null, date: date || null })
    currentRound.value = data
    roundPlayers.value = []
  }

  async function addPlayer(payload) {
    // If name not in allPlayers, create first
    let playerId = payload.player_id
    if (!playerId) {
      const existing = allPlayers.value.find(p => p.name.toLowerCase() === payload.name?.toLowerCase())
      if (existing) {
        playerId = existing.id
      } else {
        const { data: newPlayer } = await playersApi.create({ name: payload.name })
        allPlayers.value.push(newPlayer)
        playerId = newPlayer.id
      }
    }
    const { data } = await roundsApi.addPlayer(currentRound.value.id, { ...payload, player_id: playerId })
    roundPlayers.value.push(data)
    return data
  }

  async function updatePlayer(playerId, payload) {
    const { data } = await roundsApi.updatePlayer(currentRound.value.id, playerId, payload)
    const idx = roundPlayers.value.findIndex(p => p.player_id === playerId)
    if (idx >= 0) roundPlayers.value[idx] = data
    return data
  }

  async function removePlayer(playerId) {
    await roundsApi.removePlayer(currentRound.value.id, playerId)
    roundPlayers.value = roundPlayers.value.filter(p => p.player_id !== playerId)
  }

  async function finalize() {
    const { data } = await roundsApi.finalize(currentRound.value.id)
    currentRound.value = null
    roundPlayers.value = []
    return data
  }

  return {
    currentRound, roundPlayers, allPlayers,
    fetchAllPlayers, fetchCurrent, startRound,
    addPlayer, updatePlayer, removePlayer, finalize,
  }
}
