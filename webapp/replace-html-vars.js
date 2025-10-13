import fs from 'fs'
import path from 'path'

const filePath = path.resolve('public/default.html')
const outputPath = path.resolve('dist/default.html')

const env = process.env

let html = fs.readFileSync(filePath, 'utf-8')
html = html.replace(/OAUTH_CLIENT_ID/g, env.OAUTH_CLIENT_ID || '')
// Ensure output folder exists
fs.mkdirSync(path.dirname(outputPath), { recursive: true })
fs.writeFileSync(outputPath, html)
console.log('Processed default.html for environment variable interpolation.')
