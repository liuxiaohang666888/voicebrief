// VoiceBrief Worker v3 — added User-Agent so Groq doesn't block the request (1010).
// Deploy: Cloudflare Workers (free, no card). Set env var GROQ_KEY = gsk_...
// Frontend calls POST /process with { audio: dataURL, mime: "audio/xxx" }.

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

export default {
  async fetch(request, env) {
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405, cors);

    const url = new URL(request.url);
    if (url.pathname !== '/process') return json({ error: 'Not found' }, 404, cors);

    try {
      const { audio, mime } = await request.json();
      if (!audio) return json({ error: 'No audio provided' }, 400, cors);

      // decode base64 dataURL -> binary
      const base64 = audio.includes(',') ? audio.split(',')[1] : audio;
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

      // give file proper extension so Groq accepts it
      const ext = (mime || '').includes('webm') ? 'webm' : (mime || '').includes('wav') ? 'wav' : 'mp3';
      const blob = new Blob([bytes], { type: mime || 'audio/mpeg' });

      // 1) Transcribe via Groq whisper — MUST send a browser User-Agent or Groq/Cloudflare blocks (1010)
      const fd = new FormData();
      fd.append('model', 'whisper-large-v3');
      fd.append('file', blob, 'audio.' + ext);
      const tr = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + env.GROQ_KEY, 'User-Agent': UA },
        body: fd,
      });
      if (!tr.ok) {
        let t = '';
        try { t = await tr.text(); } catch (e) {}
        return json({ error: 'Transcription failed (' + tr.status + '): ' + t.slice(0, 300) }, 502, cors);
      }
      const transcript = (await tr.json()).text;

      // 2) Draft action items + reply via Groq Llama
      const sys = "You are an assistant for freelancers. Given a transcript of a client voice message, return strict JSON with exactly two keys: 'action_items' (array of short strings, each a concrete task, include any deadline mentioned) and 'reply_draft' (a short, natural professional reply the freelancer can send — confirm the tasks, friendly tone, ask only the missing clarifying question).";
      const dr = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + env.GROQ_KEY, 'Content-Type': 'application/json', 'User-Agent': UA },
        body: JSON.stringify({
          model: 'llama-3.3-70b-versatile',
          response_format: { type: 'json_object' },
          messages: [
            { role: 'system', content: sys },
            { role: 'user', content: transcript },
          ],
        }),
      });
      if (!dr.ok) {
        let t = '';
        try { t = await dr.text(); } catch (e) {}
        return json({ error: 'Draft failed (' + dr.status + '): ' + t.slice(0, 300) }, 502, cors);
      }
      const out = JSON.parse((await dr.json()).choices[0].message.content);

      return json({
        transcript,
        action_items: out.action_items || [],
        reply_draft: out.reply_draft || '',
      }, 200, cors);
    } catch (e) {
      return json({ error: String(e) }, 500, cors);
    }
  },
};

function json(data, status, headers) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...headers, 'Content-Type': 'application/json' },
  });
}
