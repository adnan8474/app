import React, { useState } from 'react';
import ProgressBar from './components/ProgressBar';

const slides = [
  {
    title: 'Evidence-Based Care & Effectiveness',
    questions: [
      'What evidence-based guidelines do you follow when using POCT devices?',
      'How do you ensure staff apply these guidelines consistently in practice?',
      'How do you ensure that the POCT devices in use on your ward are clinically effective and meet patient care needs? For example, do you review device evaluations, quality assurance results, or feedback from staff and patients?'
    ]
  },
  {
    title: 'Risk Management',
    questions: [
      'How often are risk assessments conducted for your POCT workflow (e.g., sample handling, result interpretation, infection control)?',
      'Do you have systems for capturing POCT-related incidents or near misses? Could you describe a recent event and how it was managed?'
    ]
  },
  {
    title: 'Patient & Public Involvement (PPI)',
    questions: [
      'How do you involve patients in discussions about their POCT results or processes?',
      'Do you gather patient feedback on POCT? How is this incorporated into your practice?'
    ]
  },
  {
    title: 'Clinical Audit',
    questions: [
      'How often do you perform audits on device calibration, quality control records, and result accuracy?',
      'What audit findings have been acted upon, and what were the outcomes?',
      'How do you track post-audit changes over time to ensure improvement?'
    ]
  },
  {
    title: 'Staffing & Staff Management',
    questions: [
      'Who is responsible for POCT oversight on your ward (e.g., calibration, training, quality control)?',
      'How do you identify and address performance gaps?',
      'How do you ensure clear accountability for each step of the POCT process?'
    ]
  },
  {
    title: 'Education & Training',
    questions: [
      'What initial and ongoing training do staff receive on POCT device operation, quality checks, and interpreting results?',
      'Do you use formal competency assessments or refresher courses? With what frequency?'
    ]
  },
  {
    title: 'Information & IT',
    questions: [
      'How is POCT data recorded, stored, and integrated into the electronic patient record or lab information systems?',
      'How do you ensure data accuracy and integrity?',
      'What measures protect patient data confidentiality for POCT results and records?'
    ]
  },
  {
    title: 'CQC Standards Alignment',
    questions: [
      'How does your POCT practice ensure patient safety and minimise harm (e.g., infection control, device performance checks)?',
      'How is POCT incorporated into care pathways to enhance patient outcomes based on best-practice guidelines?',
      'How is leadership provided for POCT governance? How are responsibilities, quality data, and incidents reviewed and escalated?'
    ]
  }
];

export default function App() {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState(() =>
    slides.reduce((acc, slide) => {
      slide.questions.forEach((q, i) => {
        acc[`${slide.title}-${i}`] = '';
      });
      return acc;
    }, {})
  );
  const totalSteps = slides.length + 1; // +1 for thank you slide

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const next = () => setStep((s) => Math.min(s + 1, slides.length));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  const handleSubmit = async () => {
    try {
      const res = await fetch('/.netlify/functions/submit-form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        next();
      } else {
        alert('Submission failed');
      }
    } catch (err) {
      alert('Submission error');
    }
  };

  if (step === slides.length) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-center p-4">
        <h1 className="text-2xl mb-4">Thank you for completing the POCT Governance Questionnaire</h1>
        <div className="w-16 h-16 mb-6 bg-green-500 rounded-full animate-ping" />
        <button
          onClick={() => setStep(0)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
        >
          Close
        </button>
      </div>
    );
  }

  const slide = slides[step];

  return (
    <div className="min-h-screen flex flex-col p-4">
      <div className="mb-4">
        <ProgressBar current={step + 1} total={totalSteps} />
      </div>
      <div className="flex-1 transition-all duration-500">
        {step === 0 && (
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold mb-2">Ward Clinical Governance: POCT Practices Questionnaire</h1>
            <p className="italic">"This questionnaire is designed by the POCT department to help you reflect on how your ward governs the use of Point-of-Care Testing (POCT) devices. Your responses will help us improve safety, quality, and compliance across the Trust."</p>
            <p className="mt-2">Estimated completion time: 15–20 minutes.</p>
          </div>
        )}
        <h2 className="text-xl font-semibold mb-4">{slide.title}</h2>
        <div className="space-y-4">
          {slide.questions.map((q, i) => (
            <textarea
              key={i}
              name={`${slide.title}-${i}`}
              value={formData[`${slide.title}-${i}`]}
              onChange={handleChange}
              placeholder={q}
              className="w-full p-2 rounded bg-gray-800 border border-gray-600 focus:outline-none"
              rows="3"
            />
          ))}
        </div>
      </div>
      <div className="mt-4 flex justify-between">
        <button
          onClick={prev}
          disabled={step === 0}
          className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded disabled:opacity-50"
        >
          Previous
        </button>
        {step === slides.length - 1 ? (
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded"
          >
            Submit
          </button>
        ) : (
          <button
            onClick={next}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
}
