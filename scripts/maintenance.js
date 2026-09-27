/**
 * This script can be run with node to serve the 
 * "down-for-maintenance" page at a given port number.
 * The default port number is 5300, which can be overridden
 * by supplying the port number on command line.
 */
const http = require('http')
const hostname = '127.0.0.1'
let port = 5300
const html = `<html>
    <title>AcadStack :: We are down for maintenance</title>
    <body style="text-align: center; background-color: black; color: ivory;">
        <h1>We will be back soon!</h1>
        <p style="font-size: large;">
            We are make some upgrades to our software to bring better service to you.
            We will be up and running shortly.
            <br/><br/>
            Please check back again in few minutes.
        </p>
    </body>
</html>`
myArgs = process.argv.slice(2)
if (myArgs.length > 0) port = myArgs[0]
const server = http.createServer((req, res) => {
  res.statusCode = 200
  res.setHeader('Content-Type', 'text/html')
  res.end(html)
})
server.listen(port, hostname, () => {
  console.log(`Maintenance page server running at http://${hostname}:${port}/`)
})
