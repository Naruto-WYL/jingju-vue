const API_URL = '/api/data'

export async function fetchJingjuData() {
  const response = await fetch(API_URL)

  if (!response.ok) {
    throw new Error(await response.text())
  }

  return response.json()
}
