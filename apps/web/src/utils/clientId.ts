import { nanoid } from 'nanoid'

const CLIENT_ID_KEY = 'ppt_assistant_client_id'

/**
 * 获取客户端唯一ID
 * 如果本地存储中不存在，则生成新的ID并保存
 */
export function getClientId(): string {
  let clientId = localStorage.getItem(CLIENT_ID_KEY)
  
  if (!clientId) {
    clientId = nanoid()
    localStorage.setItem(CLIENT_ID_KEY, clientId)
  }
  
  return clientId
}

/**
 * 重置客户端ID
 * 生成新的ID并替换本地存储中的值
 */
export function resetClientId(): string {
  const newClientId = nanoid()
  localStorage.setItem(CLIENT_ID_KEY, newClientId)
  return newClientId
} 