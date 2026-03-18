const DICT = {
    en: {
        nav_dashboard: 'Dashboard',
        nav_summary: 'AI Visit Summary',
        nav_meds: 'Medication Tracker',
        nav_appts: 'Appointments',

        header_patientId: 'Patient ID',
        header_signOut: 'Sign out',
        label_language: 'Language',

        dashboard_title: 'My Dashboard',
        dashboard_welcome: 'Welcome, {name}.',
        dashboard_nextAppt: 'Next appointment',
        dashboard_activeRx: 'Active prescriptions',
        dashboard_adherence: 'Medication adherence',
        dashboard_visitSummaryStatus: 'Visit summary status',
        dashboard_weeklyMeter: 'Weekly adherence meter',
        dashboard_todaysMeds: "Today’s medications",
        dashboard_upcomingAppts: 'Upcoming appointments',
        dashboard_aiSummaryHint: 'AI summary from your last visit',

        status_available: 'Available',
        status_notAvailable: 'Not available',

        adherence_good: 'Good compliance',
        adherence_excellent: 'Excellent',
        adherence_low: 'Low compliance',
        adherence_needs: 'Needs attention',

        dose_taken: 'Taken',
        dose_missed: 'Missed',
        dose_pending: 'Pending',

        meds_title: 'Medication Tracker',
        meds_desc: 'Track today’s doses and mark completion.',
        meds_meterTitle: "Today’s adherence meter",
        meds_doseCompletion: 'Dose completion: {completed} of {total} doses completed',
        meds_scheduleTitle: 'Medication schedule',
        meds_noneToday: 'No medication schedule for today.',
        meds_completed: 'Completed',
        meds_markTaken: 'Mark as Taken',
        table_medicine: 'Medicine',
        table_dosage: 'Dosage',
        table_time: 'Time',
        table_status: 'Status',
        table_action: 'Action',

        appts_title: 'Appointments',
        appts_desc: 'Upcoming appointments and past visits.',
        appts_upcoming: 'Upcoming appointments',
        appts_past: 'Past visits',
        appts_noneUpcoming: 'No upcoming appointments.',
        appts_nonePast: 'No past visits on file.',
        appts_summaryAccess: 'Summary access',
        appts_summaryNotAvailable: 'Summary not available',

        summary_title: 'AI Visit Summary',
        summary_currentLanguage: 'Current language',
        summary_notAvailable: 'AI visit summary is not available yet.',
        summary_agentIdentity: 'AI Agent Identity',
        summary_clinicalMeta: 'Clinical meta',
        summary_lastVisitDate: 'Last visit date',
        summary_treatingPhysician: 'Treating physician',
        summary_abstract: 'Patient-friendly clinical abstract (translated)',
        summary_reasoning: 'Treatment reasoning',
        summary_tips: 'Actionable health tips',
        summary_cautions: 'Cautions and warnings',
        summary_noTips: 'No tips available.',
        summary_noCautions: 'No cautions available.',

        empty_noUpcomingAppts: 'No upcoming appointments.',
        empty_noTodaysMeds: 'No medications scheduled for today.',
    },
    hi: {
        nav_dashboard: 'डैशबोर्ड',
        nav_summary: 'एआई विज़िट सारांश',
        nav_meds: 'दवा ट्रैकर',
        nav_appts: 'अपॉइंटमेंट्स',

        header_patientId: 'रोगी आईडी',
        header_signOut: 'साइन आउट',
        label_language: 'भाषा',

        dashboard_title: 'मेरा डैशबोर्ड',
        dashboard_welcome: 'स्वागत है, {name}.',
        dashboard_nextAppt: 'अगली अपॉइंटमेंट',
        dashboard_activeRx: 'सक्रिय प्रिस्क्रिप्शन',
        dashboard_adherence: 'दवा अनुपालन',
        dashboard_visitSummaryStatus: 'विज़िट सारांश स्थिति',
        dashboard_weeklyMeter: 'साप्ताहिक अनुपालन मीटर',
        dashboard_todaysMeds: 'आज की दवाएँ',
        dashboard_upcomingAppts: 'आगामी अपॉइंटमेंट्स',
        dashboard_aiSummaryHint: 'आपकी पिछली विज़िट का एआई सारांश',

        status_available: 'उपलब्ध',
        status_notAvailable: 'उपलब्ध नहीं',

        adherence_good: 'अच्छा अनुपालन',
        adherence_excellent: 'उत्कृष्ट',
        adherence_low: 'कम अनुपालन',
        adherence_needs: 'ध्यान आवश्यक',

        dose_taken: 'लिया',
        dose_missed: 'छूटा',
        dose_pending: 'बाकी',

        meds_title: 'दवा ट्रैकर',
        meds_desc: 'आज की डोज़ ट्रैक करें और पूर्ण करें।',
        meds_meterTitle: 'आज का अनुपालन मीटर',
        meds_doseCompletion: 'डोज़ पूर्णता: {completed} में से {total} डोज़ पूरी',
        meds_scheduleTitle: 'दवा शेड्यूल',
        meds_noneToday: 'आज के लिए कोई दवा शेड्यूल नहीं है।',
        meds_completed: 'पूर्ण',
        meds_markTaken: 'लिया मार्क करें',
        table_medicine: 'दवा',
        table_dosage: 'खुराक',
        table_time: 'समय',
        table_status: 'स्थिति',
        table_action: 'क्रिया',

        appts_title: 'अपॉइंटमेंट्स',
        appts_desc: 'आगामी अपॉइंटमेंट्स और पिछली विज़िटें।',
        appts_upcoming: 'आगामी अपॉइंटमेंट्स',
        appts_past: 'पिछली विज़िटें',
        appts_noneUpcoming: 'कोई आगामी अपॉइंटमेंट नहीं।',
        appts_nonePast: 'कोई पिछली विज़िट उपलब्ध नहीं।',
        appts_summaryAccess: 'सारांश देखें',
        appts_summaryNotAvailable: 'सारांश उपलब्ध नहीं',

        summary_title: 'एआई विज़िट सारांश',
        summary_currentLanguage: 'वर्तमान भाषा',
        summary_notAvailable: 'एआई विज़िट सारांश अभी उपलब्ध नहीं है।',
        summary_agentIdentity: 'एआई एजेंट पहचान',
        summary_clinicalMeta: 'क्लिनिकल जानकारी',
        summary_lastVisitDate: 'पिछली विज़िट तिथि',
        summary_treatingPhysician: 'उपचारकर्ता डॉक्टर',
        summary_abstract: 'रोगी-अनुकूल सार (अनुवादित)',
        summary_reasoning: 'उपचार का कारण',
        summary_tips: 'उपयोगी स्वास्थ्य सुझाव',
        summary_cautions: 'सावधानियाँ और चेतावनियाँ',
        summary_noTips: 'कोई सुझाव उपलब्ध नहीं।',
        summary_noCautions: 'कोई चेतावनी उपलब्ध नहीं।',

        empty_noUpcomingAppts: 'कोई आगामी अपॉइंटमेंट नहीं।',
        empty_noTodaysMeds: 'आज के लिए कोई दवा निर्धारित नहीं है।',
    },
    ta: {
        nav_dashboard: 'டாஷ்போர்டு',
        nav_summary: 'AI விஜிட் சுருக்கம்',
        nav_meds: 'மருந்து டிராக்கர்',
        nav_appts: 'நியமனங்கள்',

        header_patientId: 'நோயாளர் ஐடி',
        header_signOut: 'வெளியேறு',
        label_language: 'மொழி',

        dashboard_title: 'என் டாஷ்போர்டு',
        dashboard_welcome: 'வரவேற்கிறோம், {name}.',
        dashboard_nextAppt: 'அடுத்த நியமனம்',
        dashboard_activeRx: 'செயலில் உள்ள மருந்துகள்',
        dashboard_adherence: 'மருந்து கடைப்பிடிப்பு',
        dashboard_visitSummaryStatus: 'விஜிட் சுருக்க நிலை',
        dashboard_weeklyMeter: 'வாராந்திர கடைப்பிடிப்பு மீட்டர்',
        dashboard_todaysMeds: 'இன்றைய மருந்துகள்',
        dashboard_upcomingAppts: 'வரவிருக்கும் நியமனங்கள்',
        dashboard_aiSummaryHint: 'உங்கள் கடைசி விஜிட் AI சுருக்கம்',

        status_available: 'கிடைக்கிறது',
        status_notAvailable: 'கிடைக்கவில்லை',

        adherence_good: 'நல்ல கடைப்பிடிப்பு',
        adherence_excellent: 'மிகச்சிறப்பு',
        adherence_low: 'குறைந்த கடைப்பிடிப்பு',
        adherence_needs: 'கவனம் தேவை',

        dose_taken: 'எடுத்தது',
        dose_missed: 'தவறியது',
        dose_pending: 'நிலுவையில்',

        meds_title: 'மருந்து டிராக்கர்',
        meds_desc: 'இன்றைய டோஸ்களை கண்காணித்து முடிக்கப்பட்டதாக குறிக்கவும்.',
        meds_meterTitle: 'இன்றைய கடைப்பிடிப்பு மீட்டர்',
        meds_doseCompletion: 'டோஸ் முடிப்பு: {completed} / {total} முடிந்தது',
        meds_scheduleTitle: 'மருந்து அட்டவணை',
        meds_noneToday: 'இன்றைக்கு மருந்து அட்டவணை இல்லை.',
        meds_completed: 'முடிந்தது',
        meds_markTaken: 'எடுத்ததாக குறி',
        table_medicine: 'மருந்து',
        table_dosage: 'அளவு',
        table_time: 'நேரம்',
        table_status: 'நிலை',
        table_action: 'செயல்',

        appts_title: 'நியமனங்கள்',
        appts_desc: 'வரவிருக்கும் நியமனங்கள் மற்றும் முந்தைய விஜிட்கள்.',
        appts_upcoming: 'வரவிருக்கும் நியமனங்கள்',
        appts_past: 'முந்தைய விஜிட்கள்',
        appts_noneUpcoming: 'வரவிருக்கும் நியமனங்கள் இல்லை.',
        appts_nonePast: 'முந்தைய விஜிட்கள் பதிவு இல்லை.',
        appts_summaryAccess: 'சுருக்கத்தைப் பார்க்க',
        appts_summaryNotAvailable: 'சுருக்கம் கிடைக்கவில்லை',

        summary_title: 'AI விஜிட் சுருக்கம்',
        summary_currentLanguage: 'தற்போதைய மொழி',
        summary_notAvailable: 'AI விஜிட் சுருக்கம் இன்னும் கிடைக்கவில்லை.',
        summary_agentIdentity: 'AI ஏஜெண்ட் அடையாளம்',
        summary_clinicalMeta: 'மருத்துவ விவரங்கள்',
        summary_lastVisitDate: 'கடைசி விஜிட் தேதி',
        summary_treatingPhysician: 'சிகிச்சை மருத்துவர்',
        summary_abstract: 'நோயாளர் நட்பு சுருக்கம் (மொழிபெயர்ப்பு)',
        summary_reasoning: 'சிகிச்சை காரணம்',
        summary_tips: 'பயனுள்ள சுகாதார குறிப்புகள்',
        summary_cautions: 'எச்சரிக்கைகள்',
        summary_noTips: 'குறிப்புகள் இல்லை.',
        summary_noCautions: 'எச்சரிக்கைகள் இல்லை.',

        empty_noUpcomingAppts: 'வரவிருக்கும் நியமனங்கள் இல்லை.',
        empty_noTodaysMeds: 'இன்றைக்கு மருந்துகள் திட்டமிடப்படவில்லை.',
    },
};

function interpolate(template, vars) {
    if (!template || !vars) return template;
    return String(template).replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? `{${k}}`));
}

export function t(lang, key, vars) {
    const safeLang = DICT[lang] ? lang : 'en';
    const value = DICT[safeLang]?.[key] ?? DICT.en?.[key] ?? key;
    return interpolate(value, vars);
}

export function normalizeDoseStatus(value) {
    const v = String(value || '').trim().toLowerCase();
    if (v === 'taken' || v === 'lिया' || v === 'எடுத்தது') return 'taken';
    if (v === 'missed' || v === 'छूटा' || v === 'தவறியது') return 'missed';
    if (v === 'pending' || v === 'बाकी' || v === 'நிலுவையில்') return 'pending';
    return 'pending';
}

export function doseStatusLabel(lang, statusValue) {
    const code = normalizeDoseStatus(statusValue);
    return t(lang, `dose_${code}`);
}

export function adherenceLabel(lang, value) {
    const v = String(value || '').toLowerCase();
    if (v.includes('excellent')) return t(lang, 'adherence_excellent');
    if (v.includes('good')) return t(lang, 'adherence_good');
    if (v.includes('low')) return t(lang, 'adherence_low');
    if (v.includes('need')) return t(lang, 'adherence_needs');
    return value;
}

export function pickTranslated(value, lang) {
    if (!value) return value;
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value;
    if (typeof value === 'object') {
        return value?.[lang] ?? value?.en ?? value?.hi ?? value?.ta ?? null;
    }
    return value;
}

export function pickTranslatedList(value, lang) {
    if (!value) return [];
    if (Array.isArray(value)) return value;
    if (typeof value === 'object') {
        const list = value?.[lang] ?? value?.en ?? value?.hi ?? value?.ta ?? [];
        return Array.isArray(list) ? list : [];
    }
    return [];
}

