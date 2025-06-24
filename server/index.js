const express = require("express");
const cors = require("cors");
require("dotenv").config();

const OpenAI = require("openai");
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const app = express();
app.use(cors());
app.use(express.json());

app.post("/chat", async (req, res) => {
  const { messages } = req.body;

  try {
    const response = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: messages,
    });

    const reply = response.choices[0].message;
    res.json({ reply });
  } catch (err) {
    console.error("OpenAI Error:", err);
    res.status(500).json({ error: "Failed to generate response" });
  }
});

const port = 3001;
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
