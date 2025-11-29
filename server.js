const express = require("express");
const app = express();

app.get("/", (req, res) => {
  res.send("Bot is running 24/7!");
});

app.listen(3000, () => {
  console.log("Webserver is online!");
});
