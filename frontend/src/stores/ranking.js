import { ref } from 'vue'
import { rankingApi } from '../api'

const ranking = ref(null)

export function useRanking() {
  async function fetch() {
    const { data } = await rankingApi.get()
    ranking.value = data
  }

  async function setActive(roundIds) {
    await rankingApi.setActive(roundIds)
    if (!ranking.value) return
    ranking.value.active_round_ids = roundIds
    ranking.value.rounds.forEach(r => { r.is_active_in_ranking = roundIds.includes(r.id) })
    ranking.value.rows.forEach(row => {
      row.total = roundIds.reduce((s, rid) => s + (row.scores[String(rid)] || row.scores[rid] || 0), 0)
    })
    ranking.value.rows.sort((a, b) => b.total - a.total)
  }

  async function updateScore(playerId, roundId, score) {
    await rankingApi.updateScore(playerId, roundId, score)
    // update locally
    const row = ranking.value?.rows.find(r => r.player_id === playerId)
    if (row) {
      row.scores[String(roundId)] = score
      row.total = ranking.value.active_round_ids.reduce(
        (s, rid) => s + (row.scores[String(rid)] || 0), 0
      )
      ranking.value.rows.sort((a, b) => b.total - a.total)
    }
  }

  return { ranking, fetch, setActive, updateScore }
}
