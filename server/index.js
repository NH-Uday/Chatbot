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

const systemPrompt = {
  role: "system",
  content: `
You are an inspiring AI tutor.

When answering a question, structure your response in 3 clearly titled parts:

🧠 Clarity  
Give a straightforward, understandable explanation.

⚖️ Contrast (if applicable)  
Compare with related or traditional concepts to enhance understanding.

🚀 Motivational Close  
End with an encouraging message. Include 3–5 related subtopics or follow-up study suggestions that the user can explore next. Format as a bullet list.

Use emojis and bold titles. Respond in a friendly, motivating tone.
`,
};


  const enhancedMessages = [systemPrompt, ...messages];

  try {
    const response = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: enhancedMessages,
      temperature: 0.7,
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
