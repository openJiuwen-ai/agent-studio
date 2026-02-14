/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { WorkflowService } from '@test-agentstudio/api-client'
import { v4 as uuidv4 } from 'uuid'

export interface FileUploadParams {
  file: File
  onProgress?: (percent: number) => void
}

export interface FileUploadResult {
  url: string
  object_key: string
  metadata: {
    name: string
    size: number
    mimeType: string
  }
}

export class FileUploadService {
  /**
   * Get space_id from URL query parameters
   */
  private getSpaceIdFromUrl(): string | undefined {
    if (typeof window === 'undefined') return undefined
    const params = new URLSearchParams(window.location.search)
    return params.get('spaceId') || undefined
  }

  /**
   * Upload a file to MinIO using presigned URL
   * @param params - Upload parameters including file
   * @returns Promise with file upload result containing object_key
   */
  async uploadFile(params: FileUploadParams): Promise<{ object_key: string; name: string; size: number }> {
    const { file, onProgress } = params
    const spaceId = this.getSpaceIdFromUrl()

    if (!spaceId) {
      throw new Error('failed to found spaceId')
    }

    const objectKey = `${uuidv4()}_${file.name}`
    const uploadUrl = await this.getUploadUrl(objectKey, spaceId)
    await this.uploadToMinio(file, uploadUrl, onProgress)

    return {
      object_key: objectKey,
      name: file.name,
      size: file.size,
    }
  }

  /**
   * Upload a file and get the download URL
   * @param params - Upload parameters including file
   * @returns Promise with file upload result containing download URL and metadata
   */
  async uploadFileAndGetUrl(params: FileUploadParams): Promise<FileUploadResult> {
    const { file, onProgress } = params
    const spaceId = this.getSpaceIdFromUrl()

    if (!spaceId) {
      throw new Error('failed to found spaceId')
    }

    const uploadResult = await this.uploadFile({ file, onProgress })
    const downloadUrl = await this.getDownloadUrl(uploadResult.object_key, spaceId)

    return {
      url: downloadUrl,
      object_key: uploadResult.object_key,
      metadata: {
        name: uploadResult.name,
        size: uploadResult.size,
        mimeType: file.type,
      },
    }
  }

  /**
   * Get presigned upload URL from backend
   * @param objectKey - Object key for the file
   * @param space_id - Space ID
   * @returns Presigned upload URL
   */
  private async getUploadUrl(objectKey: string, space_id: string): Promise<string> {
    const response = await WorkflowService.getUploadUrl({
      object_key: objectKey,
      space_id,
    })

    if (response.code !== 200) {
      throw new Error(response.message || 'Failed to get upload URL')
    }

    return response.data.upload_url
  }

  /**
   * Upload file to MinIO using XMLHttpRequest for progress tracking
   * @param file - File to upload
   * @param uploadUrl - Presigned upload URL
   * @param onProgress - Optional progress callback
   */
  private uploadToMinio(file: File, uploadUrl: string, onProgress?: (percent: number) => void): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()

      xhr.upload.addEventListener('progress', e => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100)
          onProgress(percent)
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve()
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`))
        }
      })

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'))
      })

      xhr.open('PUT', uploadUrl)
      xhr.send(file)
    })
  }

  /**
   * Get download URL for a file
   * @param objectKey - Object key for the file
   * @returns Presigned download URL
   */
  async getDownloadUrl(objectKey: string, space_id: string): Promise<string> {
    const response = await WorkflowService.getDownloadUrl({
      object_key: objectKey,
      space_id: space_id,
    })

    if (response.code !== 200) {
      throw new Error(response.message || 'Failed to get download URL')
    }

    return response.data.download_url
  }
}

export const fileUploadService = new FileUploadService()
