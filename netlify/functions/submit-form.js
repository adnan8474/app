import xlsx from 'xlsx';
import sgMail from '@sendgrid/mail';

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }
  try {
    const data = JSON.parse(event.body || '{}');
    const rows = Object.entries(data).map(([key, value]) => ({ Question: key, Answer: value }));
    const worksheet = xlsx.utils.json_to_sheet(rows);
    const workbook = xlsx.utils.book_new();
    xlsx.utils.book_append_sheet(workbook, worksheet, 'Responses');
    const buffer = xlsx.write(workbook, { type: 'buffer', bookType: 'xlsx' });

    await sgMail.send({
      to: process.env.DESTINATION_EMAIL,
      from: process.env.DESTINATION_EMAIL,
      subject: 'POCT Governance Questionnaire Responses',
      text: 'See attached questionnaire results',
      attachments: [
        {
          content: buffer.toString('base64'),
          filename: 'responses.xlsx',
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          disposition: 'attachment'
        }
      ]
    });

    return {
      statusCode: 200,
      body: JSON.stringify({ message: 'ok' })
    };
  } catch (err) {
    console.error(err);
    return { statusCode: 500, body: 'Server error' };
  }
};
