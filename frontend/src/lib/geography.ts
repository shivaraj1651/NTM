export const REGIONS = {
  APAC: ['India', 'Singapore', 'Australia', 'Japan', 'South Korea', 'Thailand'],
  EMEA: ['UAE', 'UK', 'Germany', 'France', 'Saudi Arabia', 'South Africa'],
  Americas: ['USA', 'Canada', 'Brazil', 'Mexico', 'Colombia'],
} as const

export const CITIES: Record<string, string[]> = {
  // APAC
  India:       ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata'],
  Singapore:   ['Singapore City', 'Jurong East', 'Woodlands', 'Tampines', 'Clementi'],
  Australia:   ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Gold Coast'],
  Japan:       ['Tokyo', 'Osaka', 'Yokohama', 'Nagoya', 'Sapporo', 'Fukuoka'],
  'South Korea': ['Seoul', 'Busan', 'Incheon', 'Daegu', 'Daejeon', 'Gwangju'],
  Thailand:    ['Bangkok', 'Chiang Mai', 'Phuket', 'Pattaya', 'Khon Kaen'],
  // EMEA
  UAE:         ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah'],
  UK:          ['London', 'Manchester', 'Birmingham', 'Glasgow', 'Leeds', 'Liverpool'],
  Germany:     ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Cologne', 'Stuttgart'],
  France:      ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes'],
  'Saudi Arabia': ['Riyadh', 'Jeddah', 'Mecca', 'Medina', 'Dammam', 'Khobar'],
  'South Africa': ['Johannesburg', 'Cape Town', 'Durban', 'Pretoria', 'Port Elizabeth'],
  // Americas
  USA:         ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'Dallas'],
  Canada:      ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Ottawa', 'Edmonton'],
  Brazil:      ['São Paulo', 'Rio de Janeiro', 'Brasília', 'Salvador', 'Fortaleza', 'Curitiba'],
  Mexico:      ['Mexico City', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana', 'León'],
  Colombia:    ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena'],
}
